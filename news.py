import requests
from bs4 import BeautifulSoup


BASE_URL = "https://hacker-news.firebaseio.com/v0"


def get_top_story_ids(limit=5):
    """
    Get IDs of the top Hacker News stories.
    """

    url = f"{BASE_URL}/topstories.json"

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    story_ids = response.json()

    return story_ids[:limit]


def get_story(story_id):
    """
    Get complete information about one Hacker News story.
    """

    url = f"{BASE_URL}/item/{story_id}.json"

    response = requests.get(url, timeout=10)
    response.raise_for_status()

    return response.json()


def get_top_stories(limit=5):
    """
    Fetch the top Hacker News stories.

    Returns a list of story dictionaries.
    """

    story_ids = get_top_story_ids(limit)

    stories = []

    for story_id in story_ids:

        try:
            story = get_story(story_id)

            if not story:
                continue

            if story.get("type") != "story":
                continue

            stories.append(story)

        except requests.RequestException as e:

            print(
                f"Failed to fetch story {story_id}: {e}"
            )

    return stories


def clean_html(html):
    """
    Convert HTML text into clean plain text.
    """

    if not html:
        return ""

    soup = BeautifulSoup(
        html,
        "html.parser"
    )

    return soup.get_text(
        separator=" ",
        strip=True
    )


def get_story_content(story_url):
    """
    Fetch the actual article from a Hacker News story URL
    and return the first 1000 characters of readable text.
    """

    if not story_url:
        return ""

    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/151.0.0.0 Safari/537.36"
            )
        }

        response = requests.get(
            story_url,
            headers=headers,
            timeout=10
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # --------------------------------
        # Remove unnecessary HTML elements
        # --------------------------------

        for element in soup(
            [
                "script",
                "style",
                "nav",
                "footer",
                "header",
                "aside",
                "form",
                "noscript",
            ]
        ):
            element.decompose()

        # --------------------------------
        # Try article tag first
        # --------------------------------

        article = soup.find("article")

        if article:

            text = article.get_text(
                separator=" ",
                strip=True
            )

        else:

            # --------------------------------
            # Otherwise use body
            # --------------------------------

            body = soup.find("body")

            if body:

                text = body.get_text(
                    separator=" ",
                    strip=True
                )

            else:

                text = ""

        # --------------------------------
        # Return first 1000 characters
        # --------------------------------

        return text[:1000]

    except requests.RequestException as e:

        print(
            f"Failed to fetch article: {e}"
        )

        return ""

    except Exception as e:

        print(
            f"Failed to extract article content: {e}"
        )

        return ""


def get_best_story(limit=5):
    """
    Fetch the top stories and return the story
    with the highest score.
    """

    stories = get_top_stories(limit)

    if not stories:
        return None

    stories.sort(
        key=lambda story: story.get("score", 0),
        reverse=True
    )

    return stories[0]

if __name__ == "__main__":

    stories = get_top_stories(5)

    print("\nTOP 5 STORIES\n")

    for story in stories:

        print(
            f"{story.get('score', 0)} points - "
            f"{story.get('title', 'No title')}"
        )

    print("\nBEST STORY\n")

    best = get_best_story(5)

    if best:

        print("ID:", best.get("id"))
        print("Title:", best.get("title"))
        print("URL:", best.get("url"))
        print("Score:", best.get("score"))