import os
import sys
import urllib.parse
import textwrap
import requests
import django
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()

# Ensure Windows terminal prints unicode cleanly
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "project.settings")
django.setup()

import hashlib
import random
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, START, END
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq

from myapp.models import Post, UserProfile

def get_active_profile():
    return UserProfile.objects.first()

from github import (
    get_repo_files,
    get_user_repos,
    filter_meaningful_files,
    get_repo_readme,
    get_file_content,
)

from news import (
    get_top_stories,
    get_best_story,
    get_story_content,
)

from telegram import (
    send_message,
    send_photo,
    wait_for_reply,
    get_latest_update_id,
)


llm = ChatGroq(model="openai/gpt-oss-120b",temperature=0)


class TopicState(TypedDict):
    topic_source: str
    post_type: str
    repo_name: str
    file_tree: List[str]
    relevant_files: List[str]
    story_id: str
    story_title: str
    story_url: str
    story_content: str
    topic: str
    draft_text: str
    text_hash: str
    is_duplicate: bool
    image_choice: str
    image_path: str
    final_text: str



class PostTypeDecision(BaseModel):
    post_type: str = Field(description="Choose exactly one post type: 'Project' or 'News'.")

class TopicProposal(BaseModel):
    topic: str = Field(description="One specific, narrow technical topic about the repository.")
    relevant_files: List[str] = Field(description="1 to 3 relevant file paths from the provided file list.")

class NewsTopicProposal(BaseModel):
    topic: str = Field(description="A short developer-focused angle on the news story.")
    tone: str = Field(description="Choose exactly one: 'first_person' or 'neutral'.")


def select_post_type_node(state: TopicState) -> TopicState:
    last_post = Post.objects.last()
    
    # 50/50 Alternating logic: flip between Project and News
    if last_post and last_post.post_type.lower() == "project":
        final_type = "News"
    elif last_post and last_post.post_type.lower() == "news":
        final_type = "Project"
    else:
        final_type = random.choice(["Project", "News"])

    last_type_str = last_post.post_type if last_post else "None"
    print(f"\n[Post Type Selection] Selected 50/50 split -> '{final_type}' (Last post in DB was '{last_type_str}')")
    return {**state, "post_type": final_type}

def github_topic_node(state: TopicState) -> TopicState:
    profile = get_active_profile()
    gh_username = profile.github_username if (profile and profile.github_username) else "porav-cmd"
    repos = get_user_repos(gh_username)
    selected_repo = random.choice(repos) if repos else "DevFlow"
    print(f"\n[GitHub Node] Selected repository: '{selected_repo}' for user '{gh_username}' from repos: {repos}")
    
    files = get_repo_files(selected_repo)
    filtered_files = filter_meaningful_files(files)
    return {**state, "repo_name": selected_repo, "file_tree": filtered_files}

def generate_topic_node(state: TopicState) -> TopicState:
    repo_name = state["repo_name"]
    filtered_files = state["file_tree"]
    readme = get_repo_readme(repo_name)
    past_topics = list(Post.objects.filter(post_type="Project").values_list("topic", flat=True))

    files_text = "\n".join(filtered_files)
    past_topics_text = "\n".join(past_topics)

    prompt = f"""
You are analyzing a software repository to propose a technical topic.
README: {readme}
MEANINGFUL FILES: {files_text}
ALREADY POSTED TOPICS: {past_topics_text}

Task:
1. Propose ONE specific technical topic.
2. Select 1 to 3 relevant files.
Return a JSON object with exact keys "topic" and "relevant_files".
"""
    structured_llm = llm.with_structured_output(TopicProposal, method="json_mode")
    result = structured_llm.invoke(prompt)

    return {**state, "topic": result.topic, "relevant_files": result.relevant_files}

def draft_node(state: TopicState) -> TopicState:
    repo_name = state["repo_name"]
    code_chunks = []

    for file_path in state["relevant_files"]:
        try:
            content = get_file_content(repo_name, file_path)
            code_chunks.append(f"File: {file_path}\n{content}")
        except Exception as e:
            print(f"Failed to fetch {file_path}: {e}")

    code_block = "\n\n---\n\n".join(code_chunks)

    prompt = f"""
Write a technical LinkedIn post about a software project in first person.
TOPIC: {state['topic']}
RELEVANT SOURCE CODE: {code_block}

Requirements: 1400-1800 chars, casual conversational tone, max 1 code snippet (3-5 lines max), no title, no AI mentions.
"""
    response = llm.invoke(prompt)
    draft_text = response.content

    if len(draft_text) > 1800:
        shorten_prompt = f"Shorten this LinkedIn post under 1800 characters while keeping core message:\n{draft_text}"
        draft_text = llm.invoke(shorten_prompt).content

    return {**state, "draft_text": draft_text}

def fetch_news_node(state: TopicState) -> TopicState:
    stories = get_top_stories(5)
    if not stories:
        return {**state, "story_id": "", "story_title": "", "story_url": "", "story_content": ""}
    story = max(stories, key=lambda x: x.get("score", 0))
    story_content = get_story_content(story.get("url", ""))[:1000]

    return {
        **state,
        "story_id": str(story.get("id", "")),
        "story_title": story.get("title", ""),
        "story_url": story.get("url", ""),
        "story_content": story_content,
    }

def generate_news_topic_node(state: TopicState) -> TopicState:
    past_topics = list(Post.objects.filter(post_type="News").values_list("topic", flat=True))
    past_topics_text = "\n".join(past_topics)
    prompt = f"""
Create a developer angle for this news story.
TITLE: {state['story_title']}
CONTENT: {state['story_content']}
PAST TOPICS: {past_topics_text}

Return a JSON object with exact keys "topic" and "tone". Tone must be 'first_person' or 'neutral'.
"""
    structured_llm = llm.with_structured_output(NewsTopicProposal, method="json_mode")
    result = structured_llm.invoke(prompt)
    return {**state, "topic": result.topic}

def news_draft_node(state: TopicState) -> TopicState:
    prompt = f"""
Write a technology news LinkedIn post for developers.
TOPIC: {state['topic']}
HEADLINE: {state['story_title']}
CONTENT: {state['story_content']}
Requirements: 1200-1600 chars, strong hook, conversational tone, no title.
"""
    draft_text = llm.invoke(prompt).content
    return {**state, "draft_text": draft_text}

def dedup_node(state: TopicState) -> TopicState:
    draft = state["draft_text"]
    text_hash = hashlib.sha256(draft.encode("utf-8")).hexdigest()
    is_dup = Post.objects.filter(text_hash=text_hash).exists()
    return {**state, "text_hash": text_hash, "is_duplicate": is_dup}

def ask_image_node(state: TopicState) -> TopicState:
    message = (
        "Do you want an AI-generated image for this post?\n\n"
        "Reply with:\nyes\nor\nno"
    )
    print("\n[Telegram] Asking user about image preference...")

    latest_update_id = get_latest_update_id()
    starting_offset = 0 if latest_update_id is None else latest_update_id + 1

    send_message(message)
    reply = wait_for_reply(starting_offset)
    reply = reply.strip().lower()

    image_choice = "yes" if reply in ["yes", "y"] else "no"
    print(f"[Telegram] Received response: '{reply}' -> Choice: '{image_choice}'")
    return {**state, "image_choice": image_choice}

class InfographicDetails(BaseModel):
    title: str = Field(description="Short, punchy title under 40 characters")
    objectives: List[str] = Field(description="3 short key objective bullet points")
    time_complexity: str = Field(description="Exact time complexity e.g. O(1) or O(N)")
    space_complexity: str = Field(description="Exact space complexity e.g. O(1) or O(N)")
    workflow_steps: List[str] = Field(description="4 clear step-by-step workflow stages")
    takeaways: List[str] = Field(description="3 practical best practice takeaways")

def generate_infographic_details(topic: str, draft_text: str) -> InfographicDetails:
    prompt = f"""
Extract and generate 100% accurate, topic-specific technical details for an infographic cheat sheet.

TOPIC: {topic}
DRAFT POST: {draft_text}

Task:
1. 'title': Short title under 40 chars.
2. 'objectives': List of 3 concise key technical goals.
3. 'time_complexity': Exact time complexity or primary runtime metric (e.g. "O(1) Async" or "O(N log N)").
4. 'space_complexity': Exact space complexity or memory metric (e.g. "O(1) Memory" or "O(N)").
5. 'workflow_steps': List of 4 step-by-step execution stages.
6. 'takeaways': List of 3 practical developer best practices.

Return a JSON object with exact keys "title", "objectives", "time_complexity", "space_complexity", "workflow_steps", and "takeaways".
"""
    try:
        structured_llm = llm.with_structured_output(InfographicDetails, method="json_mode")
        return structured_llm.invoke(prompt)
    except Exception as e:
        print(f"Infographic detail LLM generation fallback ({e})")
        return InfographicDetails(
            title=topic[:38],
            objectives=["Decouple heavy blocking operations", "Non-blocking fast API response (<50ms)", "Clean modular architecture"],
            time_complexity="O(1) Async",
            space_complexity="O(1) Memory",
            workflow_steps=[
                "Step 1 -> Client sends HTTP/WS request to Endpoint",
                "Step 2 -> Backend validates token & processes event",
                "Step 3 -> Worker processes task asynchronously",
                "Step 4 -> Result dispatched & saved to Database"
            ],
            takeaways=["Keep payloads lightweight (pass IDs, not large objects)", "Ensure idempotent execution for safe retries", "Decouple web servers from background workers"]
        )

def draw_code_snippet(draw, x, y, code_text, font):
    keywords = {"def", "class", "return", "import", "from", "if", "else", "elif", "for", "while", "try", "except", "with", "as", "async", "await", "not", "in", "is", "True", "False", "None"}
    decorators = {"@csrf_exempt", "@shared_task", "@receiver", "@property", "@staticmethod", "@classmethod"}

    lines = code_text.split("\n")[:10]
    curr_y = y
    for line in lines:
        tokens = line.split(" ")
        curr_x = x
        for token in tokens:
            color = (220, 220, 220)
            clean_tok = token.strip("():,[]{}'\"")
            
            if token.startswith("#"):
                color = (106, 153, 85)
            elif token in decorators or any(token.startswith(d) for d in decorators):
                color = (220, 220, 170)
            elif clean_tok in keywords:
                color = (86, 156, 214)
            elif token.startswith('"') or token.startswith("'") or token.endswith('"') or token.endswith("'"):
                color = (206, 145, 120)
            
            draw.text((curr_x, curr_y), token + " ", fill=color, font=font)
            try:
                bbox = font.getbbox(token + " ")
                tok_width = bbox[2] - bbox[0]
            except Exception:
                tok_width = len(token + " ") * 11
            curr_x += tok_width
        curr_y += 26

def generate_handwritten_cheatsheet(topic: str, draft_text: str, output_path: str = "generated_image.jpg") -> str:
    try:
        details = generate_infographic_details(topic, draft_text)
        
        # 1200 x 1800 high-res canvas (Cream Paper Aesthetic)
        img = Image.new("RGB", (1200, 1800), color=(254, 252, 248))
        draw = ImageDraw.Draw(img)

        # Draw grid paper lines (30px spacing)
        for y in range(0, 1800, 30):
            draw.line([(0, y), (1200, y)], fill=(238, 233, 222), width=1)
        for x in range(0, 1200, 30):
            draw.line([(x, 0), (x, 1800)], fill=(238, 233, 222), width=1)

        # Handwritten Fonts
        try:
            title_font = ImageFont.truetype("comicbd.ttf", 34)
            heading_font = ImageFont.truetype("comicbd.ttf", 22)
            body_font = ImageFont.truetype("comic.ttf", 19)
            small_font = ImageFont.truetype("comic.ttf", 15)
            code_font = ImageFont.truetype("consola.ttf", 16)
        except Exception:
            title_font = heading_font = body_font = small_font = code_font = ImageFont.load_default()

        # Top Left Title with Purple Underline
        raw_title = details.title if (hasattr(details, 'title') and details.title) else topic
        clean_title = textwrap.shorten(raw_title, width=42, placeholder="...")
        draw.text((40, 35), clean_title, fill=(30, 30, 30), font=title_font)
        draw.line([(40, 78), (580, 78)], fill=(120, 60, 180), width=3)

        # Top Right Sticky Note: GOAL (Yellow with Drop Shadow)
        draw.rectangle([665, 35, 1165, 235], fill=(225, 215, 180))
        draw.rectangle([660, 30, 1160, 230], fill=(255, 248, 185), outline=(220, 195, 80), width=2)
        draw.text((680, 45), "GOAL", fill=(160, 80, 0), font=heading_font)
        draw.line([(680, 72), (740, 72)], fill=(160, 80, 0), width=2)
        
        objs = details.objectives if (hasattr(details, 'objectives') and details.objectives) else ["Decouple blocking ops", "Non-blocking API response"]
        goals_text = "\n".join([f"• {g}" for g in objs[:3]])
        draw.text((680, 85), goals_text, fill=(50, 50, 50), font=body_font)

        # Middle Right Sticky Note: COMPLEXITY (Green with Drop Shadow)
        draw.rectangle([665, 265, 1165, 465], fill=(210, 230, 210))
        draw.rectangle([660, 260, 1160, 460], fill=(230, 248, 230), outline=(130, 195, 130), width=2)
        draw.text((680, 275), "COMPLEXITY", fill=(30, 110, 40), font=heading_font)
        draw.line([(680, 302), (810, 302)], fill=(30, 110, 40), width=2)
        
        time_c = details.time_complexity if (hasattr(details, 'time_complexity') and details.time_complexity) else "O(1) Async"
        space_c = details.space_complexity if (hasattr(details, 'space_complexity') and details.space_complexity) else "O(1) Memory"
        comp_text = f"Time Complexity : {time_c}\n(Each element processed once)\n\nSpace Complexity : {space_c}\n(Uses fixed memory resources)"
        draw.text((680, 315), comp_text, fill=(40, 40, 40), font=body_font)

        # Top Left Code Box (Purple Outline)
        draw.rectangle([40, 100, 630, 500], fill=(250, 250, 255), outline=(120, 80, 180), width=2)
        
        code_text = ""
        if "```" in draft_text:
            parts = draft_text.split("```")
            if len(parts) >= 2:
                raw_code = parts[1].strip()
                lines = raw_code.split("\n")
                if lines and lines[0].lower() in ["python", "bash", "json"]:
                    lines = lines[1:]
                code_text = "\n".join(lines[:12])

        if not code_text:
            code_text = "def process_request(data):\n    # Core execution handler\n    result = execute_task(data)\n    return result"

        draw_code_snippet(draw, 55, 115, code_text, code_font)

        # Section Header: HOW IT WORKS?
        draw.text((40, 520), "HOW IT WORKS ?", fill=(120, 40, 40), font=heading_font)
        draw.line([(40, 548), (220, 548)], fill=(120, 40, 40), width=2)

        # 6-Box Workflow Grid (2 rows x 3 cols)
        steps = details.workflow_steps if (hasattr(details, 'workflow_steps') and details.workflow_steps) else [
            "Initialize request params",
            "Validate authentication token",
            "Dispatch payload to queue",
            "Process task in background",
            "Log execution metrics",
            "Return success response"
        ]
        
        box_w, box_h = 360, 180
        col_gap, row_gap = 20, 20
        start_x, start_y = 40, 565

        for idx in range(min(6, len(steps))):
            r = idx // 3
            c = idx % 3
            bx = start_x + c * (box_w + col_gap)
            by = start_y + r * (box_h + row_gap)

            draw.rectangle([bx, by, bx + box_w, by + box_h], fill=(255, 255, 255), outline=(180, 180, 190), width=2)
            draw.ellipse([bx + 12, by + 12, bx + 42, by + 42], fill=(240, 240, 250), outline=(80, 80, 120), width=2)
            draw.text((bx + 21, by + 15), str(idx + 1), fill=(40, 40, 100), font=heading_font)
            
            step_desc = steps[idx]
            wrapped_step = "\n".join(textwrap.wrap(step_desc, width=26))
            draw.text((bx + 50, by + 15), wrapped_step, fill=(40, 40, 40), font=body_font)

        # Section Header: DRY RUN TABLE (Bottom Left)
        draw.text((40, 990), "DRY RUN :", fill=(30, 30, 30), font=heading_font)
        
        # Table Header
        draw.rectangle([40, 1025, 630, 1065], fill=(235, 240, 245), outline=(100, 100, 100), width=2)
        draw.text((55, 1033), "Step", fill=(30, 30, 30), font=heading_font)
        draw.text((140, 1033), "Left Val", fill=(30, 30, 30), font=heading_font)
        draw.text((280, 1033), "Right Val", fill=(30, 30, 30), font=heading_font)
        draw.text((440, 1033), "Action Result", fill=(30, 30, 30), font=heading_font)

        sample_rows = [
            ("1", "req_id", "valid", "Match [✓]"),
            ("2", "token", "valid", "Match [✓]"),
            ("3", "payload", "processed", "Match [✓]"),
            ("4", "result", "complete", "Success [✓]")
        ]
        
        ty = 1065
        for r_idx, (st, lv, rv, act) in enumerate(sample_rows):
            draw.rectangle([40, ty, 630, ty + 40], fill=(255, 255, 255), outline=(180, 180, 180), width=1)
            draw.text((65, ty + 8), st, fill=(40, 40, 40), font=body_font)
            draw.text((150, ty + 8), lv, fill=(40, 40, 40), font=body_font)
            draw.text((290, ty + 8), rv, fill=(40, 40, 40), font=body_font)
            color = (30, 120, 40) if "✓" in act or "Match" in act or "Success" in act else (180, 40, 40)
            draw.text((450, ty + 8), act, fill=color, font=body_font)
            ty += 40

        # Pink Sticky Note Bottom Right: TAKEAWAYS
        draw.rectangle([665, 1030, 1165, 1260], fill=(235, 210, 220))
        draw.rectangle([660, 1025, 1160, 1255], fill=(255, 230, 238), outline=(220, 140, 160), width=2)
        draw.text((680, 1040), "TAKEAWAYS", fill=(170, 30, 70), font=heading_font)
        draw.line([(680, 1067), (790, 1067)], fill=(170, 30, 70), width=2)

        tkaways = details.takeaways if (hasattr(details, 'takeaways') and details.takeaways) else ["Keep payloads light", "Ensure idempotency", "Monitor queues"]
        takeaway_text = "\n".join([f"• {t}" for t in tkaways[:3]])
        draw.text((680, 1080), takeaway_text, fill=(50, 50, 50), font=body_font)

        # Purple Sticky Note Bottom Right: KEY CONCEPT Q&A
        draw.rectangle([665, 1290, 1165, 1490], fill=(220, 210, 240))
        draw.rectangle([660, 1285, 1160, 1485], fill=(238, 230, 255), outline=(160, 140, 210), width=2)
        draw.text((680, 1300), "KEY CONCEPT", fill=(80, 40, 140), font=heading_font)
        draw.line([(680, 1327), (810, 1327)], fill=(80, 40, 140), width=2)
        draw.text((680, 1340), "When do we return False?\nWhen validation fails or a timeout occurs.\nThen terminate early to save compute.", fill=(50, 50, 50), font=body_font)

        img.save(output_path, quality=95)
        print(f"Handwritten Cheat Sheet generated successfully: {output_path}")
        return output_path
    except Exception as e:
        print(f"Handwritten cheat sheet generation error ({e})")
        return ""

def image_node(state: TopicState) -> TopicState:
    topic = state.get("topic", "software development")
    draft_text = state.get("draft_text", "")
    print("Generating 100% crisp, handwritten cheat sheet image on grid paper for topic:", topic)
    image_path = generate_handwritten_cheatsheet(topic, draft_text, "generated_image.jpg")
    return {**state, "image_path": image_path}

def send_final_telegram_node(state: TopicState) -> TopicState:
    draft_text = state["draft_text"]
    image_choice = state.get("image_choice", "no")
    image_path = state.get("image_path", "")

    print("\n[Telegram] Sending final draft to Telegram...")
    if image_choice == "yes" and image_path and os.path.exists(image_path):
        print(f"[Telegram] Sending photo ({image_path}) + text draft to Telegram...")
        send_photo(image_path, caption=draft_text)
    else:
        print("[Telegram] Sending text-only draft to Telegram...")
        send_message(f"📢 Here is your final post draft:\n\n{draft_text}")

    return {**state, "final_text": draft_text}

def save_node(state: TopicState) -> TopicState:
    profile = get_active_profile()
    post_type = state["post_type"].capitalize()
    post = Post.objects.create(
        user=profile.user if profile else None,
        topic=state["topic"],
        post_type=post_type,
        final_text=state["draft_text"],
        text_hash=state["text_hash"],
        image_type="FREE" if state.get("image_choice") == "yes" else "NONE",
        image_path=state.get("image_path", ""),
    )
    user_str = profile.user.username if profile else "Anonymous"
    print(f"Post saved in database with ID: {post.id} for user: {user_str}")
    return {**state, "final_text": state["draft_text"]}

# ============================================================
# ROUTERS
# ============================================================

def route_on_post_type(state: TopicState) -> str:
    post_type = state["post_type"].lower()
    return "github_topic" if post_type == "project" else ("fetch_news" if post_type == "news" else "__end__")

def route_on_duplicate(state: TopicState) -> str:
    return "__end__" if state["is_duplicate"] else "ask_image"

def route_on_image_choice(state: TopicState) -> str:
    return "image" if state.get("image_choice") == "yes" else "send_final"

# ============================================================
# BUILD GRAPH
# ============================================================

graph = StateGraph(TopicState)

graph.add_node("select_post_type", select_post_type_node)
graph.add_node("github_topic", github_topic_node)
graph.add_node("generate_topic", generate_topic_node)
graph.add_node("draft", draft_node)
graph.add_node("fetch_news", fetch_news_node)
graph.add_node("generate_news_topic", generate_news_topic_node)
graph.add_node("news_draft", news_draft_node)
graph.add_node("dedup", dedup_node)
graph.add_node("ask_image", ask_image_node)
graph.add_node("image", image_node)
graph.add_node("send_final", send_final_telegram_node)
graph.add_node("save", save_node)

# Flow logic:
# START -> select_post_type -> route_on_post_type -> (github_topic | fetch_news)
graph.add_edge(START, "select_post_type")

graph.add_conditional_edges(
    "select_post_type",
    route_on_post_type,
    {
        "github_topic": "github_topic",
        "fetch_news": "fetch_news",
        "__end__": END,
    }
)

# Project path:
graph.add_edge("github_topic", "generate_topic")
graph.add_edge("generate_topic", "draft")
graph.add_edge("draft", "dedup")

# News path:
graph.add_edge("fetch_news", "generate_news_topic")
graph.add_edge("generate_news_topic", "news_draft")
graph.add_edge("news_draft", "dedup")

# Dedup -> route_on_duplicate -> ask_image (or END if duplicate)
graph.add_conditional_edges(
    "dedup",
    route_on_duplicate,
    {
        "ask_image": "ask_image",
        "__end__": END,
    }
)

# ask_image -> route_on_image_choice -> (image | send_final)
graph.add_conditional_edges(
    "ask_image",
    route_on_image_choice,
    {
        "image": "image",
        "send_final": "send_final",
    }
)

# image -> send_final -> save -> END
graph.add_edge("image", "send_final")
graph.add_edge("send_final", "save")
graph.add_edge("save", END)

app = graph.compile()

# ============================================================
# EXECUTION
# ============================================================

initial_state: TopicState = {
    "topic_source": "",
    "post_type": "",
    "repo_name": "DevFlow",
    "file_tree": [],
    "relevant_files": [],
    "story_id": "",
    "story_title": "",
    "story_url": "",
    "story_content": "",
    "topic": "",
    "draft_text": "",
    "text_hash": "",
    "is_duplicate": False,
    "image_choice": "",
    "image_path": "",
    "final_text": "",
}

if __name__ == "__main__":
    print("Starting pipeline execution...")
    result = app.invoke(initial_state)

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 60)
    print("Post Type:", result["post_type"])
    print("Topic:", result["topic"])
    print("Image Choice:", result["image_choice"])
    print("\nDraft Post:\n")
    print(result["final_text"])