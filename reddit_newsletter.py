import praw
import time
import os

from langchain.tools import tool
from langchain.llms import Ollama
from crewai import Agent, Task, Process, Crew


from langchain.agents import load_tools

# To load Human in the loop
human_tools = load_tools(["human"])

# To Load GPT-4
api = os.environ.get("OPENAI_API_KEY")


# To Load Local models through Ollama
mistral = Ollama(model="mistral")


class BrowserTool:
    @tool("Scrape reddit content")
    def scrape_reddit(max_comments_per_post=7):
        """Useful to scrape a reddit content"""
        reddit = praw.Reddit(
            client_id="client-id",
            client_secret="client-secret",
            user_agent="user-agent",
        )
        subreddit = reddit.subreddit("LocalLLaMA")
        scraped_data = []

        for post in subreddit.hot(limit=12):
            post_data = {"title": post.title, "url": post.url, "comments": []}

            try:
                post.comments.replace_more(limit=0)  # Load top-level comments only
                comments = post.comments.list()
                if max_comments_per_post is not None:
                    comments = comments[:7]

                for comment in comments:
                    post_data["comments"].append(comment.body)

                scraped_data.append(post_data)

            except praw.exceptions.APIException as e:
                print(f"API Exception: {e}")
                time.sleep(60)  # Sleep for 1 minute before retrying

        return scraped_data


"""
- define agents that are going to research latest AI tools and write a blog about it 
- explorer will use access to internet and LocalLLama subreddit to get all the latest news
- writer will write drafts 
- critique will provide feedback and make sure that the blog text is engaging and easy to understand
"""

explorer = Agent(
    role="Senior Researcher",
    goal="Find and explore the most exciting projects and companies on LocalLLama subreddit in 2024",
    backstory="""You are and Expert strategist that knows how to spot emerging trends and companies in AI, tech and machine learning. 
    You're great at finding interesting, exciting projects on LocalLLama subreddit. You turned scraped data into detailed reports with names
    of most exciting projects an companies in the ai/ml world. ONLY use scraped data from LocalLLama subreddit for the report.
    """,
    verbose=True,
    allow_delegation=False,
    tools=[BrowserTool().scrape_reddit] + human_tools,
    llm=mistral,  # remove to use default gpt-4
)

writer = Agent(
    role="Senior Technical Writer",
    goal="Write engaging and interesting blog post about latest AI projects using simple, layman vocabulary",
    backstory="""You are an Expert Writer on technical innovation, especially in the field of AI and machine learning. You know how to write in 
    engaging, interesting but simple, straightforward and concise. You know how to present complicated technical terms to general audience in a 
    fun way by using layman words.ONLY use scraped data from LocalLLama subreddit for the blog.""",
    verbose=True,
    allow_delegation=True,
    llm=mistral,  # remove to use default gpt-4
)
critic = Agent(
    role="Expert Writing Critic",
    goal="Provide feedback and criticize blog post drafts. Make sure that the tone and writing style is compelling, simple and concise",
    backstory="""You are an Expert at providing feedback to the technical writers. You can tell when a blog text isn't concise,
    simple or engaging enough. You know how to provide helpful feedback that can improve any text. You know how to make sure that text 
    stays technical and insightful by using layman terms.
    """,
    verbose=True,
    allow_delegation=True,
    llm=mistral,  # remove to use default gpt-4
)

task_report = Task(
    description="""Use and summarize scraped data from subreddit LocalLLama to make a detailed report on the latest rising projects in AI. Use ONLY 
    scraped data from LocalLLama to generate the report. Your final answer MUST be a full analysis report, text only, ignore any code or anything that 
    isn't text. The report has to have bullet points and with 5-10 exciting new AI projects and tools. Write names of every tool and project. 
    Each bullet point MUST contain 3 sentences that refer to one specific ai company, product, model or anything you found on subreddit LocalLLama.  
    """,
    agent=explorer,
)

task_blog = Task(
    description="""Write a blog article with text only and with a short but impactful headline and at least 10 paragraphs. Blog should summarize 
    the report on latest ai tools found on localLLama subreddit. Style and tone should be compelling and concise, fun, technical but also use 
    layman words for the general public. Name specific new, exciting projects, apps and companies in AI world. Don't 
    write "**Paragraph [number of the paragraph]:**", instead start the new paragraph in a new line. Write names of projects and tools in BOLD.
    ALWAYS include links to projects/tools/research papers. ONLY include information from LocalLLAma.
    For your Outputs use the following markdown format:
    ```
    ## [Title of post](link to project)
    - Interesting facts
    - Own thoughts on how it connects to the overall theme of the newsletter
    ## [Title of second post](link to project)
    - Interesting facts
    - Own thoughts on how it connects to the overall theme of the newsletter
    ```
    """,
    agent=writer,
)

task_critique = Task(
    description="""The Output MUST have the following markdown format:
    ```
    ## [Title of post](link to project)
    - Interesting facts
    - Own thoughts on how it connects to the overall theme of the newsletter
    ## [Title of second post](link to project)
    - Interesting facts
    - Own thoughts on how it connects to the overall theme of the newsletter
    ```
    Make sure that it does and if it doesn't, rewrite it accordingly.
    """,
    agent=critic,
)

# instantiate crew of agents
crew = Crew(
    agents=[explorer, writer, critic],
    tasks=[task_report, task_blog, task_critique],
    verbose=2,
    process=Process.sequential,  # Sequential process will have tasks executed one after the other and the outcome of the previous one is passed as extra content into this next.
)

# Get your crew to work!
result = crew.kickoff()

print("######################")
print(result)
