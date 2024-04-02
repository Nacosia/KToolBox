from datetime import datetime
from typing import Optional, List, Generator, Any, Tuple
import hashlib
import json

from loguru import logger
from pathvalidate import sanitize_filename

from ktoolbox.api.model import Post
from ktoolbox.configuration import config
from ktoolbox.job import CreatorIndices

__all__ = ["generate_post_path_name", "filter_posts_by_time", "filter_posts_by_indices"]


def generate_post_path_name(post: Post) -> str:
    """Generate directory name for post to save."""
    if config.job.post_id_as_path or not post.title:
        return post.id
    else:
        time_format = "%Y-%m-%d"
        try:
            return sanitize_filename(
                config.job.post_dirname_format.format(
                    id=post.id,
                    user=post.user,
                    service=post.service,
                    title=post.title,
                    added=post.added.strftime(time_format) if post.added else "",
                    published=post.published.strftime(time_format) if post.published else "",
                    edited=post.edited.strftime(time_format) if post.edited else ""
                )
            )
        except KeyError as e:
            logger.error(f"`JobConfiguration.post_dirname_format` contains invalid key: {e}")
            exit(1)


def _match_post_time(
        post: Post,
        start_time: Optional[datetime],
        end_time: Optional[datetime]
) -> bool:
    """
    Check if the post publish date match the time range.

    :param post: Target post object
    :param start_time: Start time of the time range
    :param end_time: End time of the time range
    :return: Whether if the post publish date match the time range
    """
    if start_time and post.published < start_time:
        return False
    if end_time and post.published > end_time:
        return False
    return True


def filter_posts_by_time(
        post_list: List[Post],
        start_time: Optional[datetime],
        end_time: Optional[datetime]
) -> Generator[Post, Any, Any]:
    """
    Filter posts by publish time range

    :param post_list: List of posts
    :param start_time: Start time of the time range
    :param end_time: End time of the time range
    """
    post_filter = filter(lambda x: _match_post_time(x, start_time, end_time), post_list)
    yield from post_filter


def filter_posts_by_indices(posts: List[Post], indices: CreatorIndices) -> Tuple[List[Post], CreatorIndices]:
    """
    Compare and filter posts by ``CreatorIndices`` data

    Only keep posts that was edited after last download.

    :param posts: Posts to filter
    :param indices: ``CreatorIndices`` data to use
    :return: A updated ``List[Post]`` and updated **new** ``CreatorIndices`` instance
    """
    new_list = list(
        filter(
            lambda x: x.id not in indices.posts or x.edited > indices.posts[x.id].edited, posts
        )
    )
    new_indices = indices.model_copy(deep=True)
    for post in new_list:
        new_indices.posts[post.id] = post
    return new_list, new_indices

def json_hash(d, sorted_list=False):
    """
    Calculate the hash value of a JSON object.

    Parameters:
    - d: The JSON object to calculate the hash for.
    - about_list: A boolean indicating whether the hash should consider the order of list elements.

    Returns:
    - The hash value of the JSON object.
    """

    def sort_list(l):
        for i, v in enumerate(l):
            if isinstance(v, dict):
                l[i] = f"dict-{hash_dict(v)}"
            elif isinstance(v, list):
                l[i] = sort_list(v)
        if sorted_list:
            return sorted(l, key=lambda x: (str(type(x)), x))
        return l
        
    def hash_list(l):
        return hashlib.sha256(json.dumps(sort_list(l)).encode()).hexdigest()

    def hash_dict(d):
        for k, v in d.items():
            if isinstance(v, dict):
                d[k] = f"dict-{hash_dict(v)}"
            elif isinstance(v, list):
                d[k] = sort_list(v)
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()
    
    def hash_value(v):
        return hashlib.sha256(str(v).encode()).hexdigest()
    
    def hash_json(json_data):
        if isinstance(json_data, dict):
            return hash_dict(json_data)
        elif isinstance(json_data, list):
            return hash_list(json_data)
        else:
            return hash_value(json_data)
    
    return hash_json(d)