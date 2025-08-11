from datetime import datetime, timedelta

from loguru import logger


def ensure_datetime(date_string: str) -> datetime:
    """Parse date string in various formats and return a datetime object."""
    
    match date_string:
        case "today":
            return datetime.now()
        case "yesterday":
            return datetime.now() - timedelta(days=1)
        case "last_week":
            return datetime.now() - timedelta(days=7)
        case "last_month":
            return datetime.now() - timedelta(days=30)
        case "last_year":
            return datetime.now() - timedelta(days=365)
        case _:
            logger.info(f"Parsing date: {date_string}")            
            formats = [
                '%Y-%m-%d',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y-%m-%d %H:%M:%S',
                '%m/%d/%Y %H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    return datetime.strptime(date_string, fmt)
                except ValueError:
                    continue
            
            raise ValueError(f"Unable to parse date: {date_string}")

def get_current_prompt(topic: str, start_period: str = "yesterday", end_period: str = "today", number_of_news_items: int = 10, location: str = "San Francisco") -> str:
    """Retrieve the current prompt for the topic fromt the database/filesystem"""
    # TODO: Implement the logic to retrieve the best prompt
    prompt = f"""Review user Gmail emails from {start_period} to {end_period} and identify senders corresponding to {topic}-related newsletters. 
    Do not use any other sources of information but the emails.
    For each identified newsletter, read all issues from the past month. From these, compile a 
    digest of at least {number_of_news_items} notable AI news items. For each news item include at least:
        - Include a one-line summary as a headline.
        - Add the publication date.
        - Provide a brief, clear technical summary for a knowledgeable audience.
        - Insert a clickable source link.
        - Assign an importance rating from 1 (minor) to 5 (high impact).
        - Organize the news chronologically or by theme for readability.
    At the end, include a separate section listing {topic}-related events happening in {location} during the current month, with event names, dates, venues, and source links.
    Ensure the digest is concise, technically accurate, and accessible to expert readers, while preserving essential details and trends.
    To distill the news, use only the information provided in the emails. Do an exhaustive search in the emails retrieving all the information available to satisfy the request requirements.
    """
    return prompt