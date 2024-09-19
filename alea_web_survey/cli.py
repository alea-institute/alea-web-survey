"""
CLI utility for ALEA Web Survey.
"""

# imports
import argparse
import asyncio
import sys

# project
from alea_web_survey.tasks.collect_web import collect_sites
from alea_web_survey.tasks.collect_web_parallel import collect_sites_parallel
from alea_web_survey.tasks.get_resource import get_resource
from alea_web_survey.tasks.push_s3 import push_cache

# packages


def main():
    """
    Main entry point for the CLI.

    Returns:
        None
    """
    # create the argument parser with a subparser for each task.
    # collect: max-sites, push-every
    # push: remove-after
    # print: url
    parser = argparse.ArgumentParser(description="CLI utility for ALEA Web Survey.")
    subparsers = parser.add_subparsers(dest="task", help="Task to perform.")

    # collect
    collect_parser = subparsers.add_parser("collect", help="Collect web resources.")
    collect_parser.add_argument(
        "--max_sites",
        type=int,
        default=None,
        help="Maximum number of sites to collect.",
    )
    collect_parser.add_argument(
        "--push_every",
        type=int,
        default=None,
        help="Number of sites to collect before pushing.",
    )

    # collect_parallel
    collect_parallel_parser = subparsers.add_parser(
        "collect_parallel", help="Collect web resources in parallel."
    )
    collect_parallel_parser.add_argument(
        "--max_sites",
        type=int,
        default=None,
        help="Maximum number of sites to collect.",
    )
    collect_parallel_parser.add_argument(
        "--push_every",
        type=int,
        default=None,
        help="Maximum number of sites to collect.",
    )
    collect_parallel_parser.add_argument(
        "--max_workers",
        type=int,
        default=8,
        help="Maximum number of worker threads.",
    )

    # push
    push_parser = subparsers.add_parser("push", help="Push collected resources.")
    push_parser.add_argument(
        "--remove-after",
        action="store_true",
        help="Remove local resources after pushing.",
    )

    # print
    print_parser = subparsers.add_parser("print", help="Print a web resource.")
    print_parser.add_argument("url", type=str, help="URL of the resource to print.")

    args = parser.parse_args()

    # run the task
    if args.task == "collect":
        if args.push_every:
            # loop in batches of push_every
            batch_number = 0
            while True:
                asyncio.run(collect_sites(max_sites=args.push_every))
                asyncio.run(push_cache(remove_after=True))
                batch_number += 1
        else:
            # run normally
            asyncio.run(collect_sites(args.max_sites))
    elif args.task == "collect_parallel":
        if args.push_every:
            # loop in batches of push_every
            batch_number = 0
            while True:
                asyncio.run(collect_sites_parallel(args.push_every, args.max_workers))
                asyncio.run(push_cache(remove_after=True))
                batch_number += 1
        else:
            # run normally
            asyncio.run(collect_sites(args.max_sites))
    elif args.task == "push":
        # push the cache
        asyncio.run(push_cache(args.remove_after))
    elif args.task == "print":
        # print a resource by url
        content = get_resource(args.url)
        try:
            content = content.decode("utf-8")
        except UnicodeDecodeError:
            pass
        sys.stdout.write(content)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
