import click
import requests
from conf import config
from github import Github
from typing import Optional

# def _set_label_decrease(pull, before_label: str) -> str:
#     if before_label == "D-5":
#         pull.set_labels("D-4")
#         return "D-4"
#
#     elif before_label == "D-4":
#         pull.set_labels("D-3")
#         return "D-3"
#
#     elif before_label == "D-3":
#         pull.set_labels("D-2")
#         return "D-2"
#
#     elif before_label == "D-2":
#         pull.set_labels("D-1")
#         return "D-1"
#     else:
#         pull.set_labels("D-0")
#         return "D-0"


def _send_slack(slack_webhook_url: str, msg: str):
    payload = {"text": msg}
    requests.post(slack_webhook_url, json=payload)


def _make_pr_link_with_no(clone_url: str, pr_no: int) -> str:
    return f'{clone_url.replace(".git", "")}/pull/{pr_no}'


def _get_target_pull_requests(repo):
    # target_pull_requests_count = 0
    target_pull_requests = []

    # Gets the list of currently open PRs.
    for pull in repo.get_pulls(
        state="open",
        sort="updated",
    ):
        approved_count = 0
        for item in pull.get_reviews():
            if item.state == "APPROVED":
                approved_count += 1
        # PRs approved by more than one person are not eligible.
        if approved_count > 1:
            continue

        # Exclude from the list if the review is an ongoing PR
        # pr_comments_count = pull.review_comments
        # if pr_comments_count != 0:
        #     pass
        # else:
        #     target_pull_requests_count += 1
        #     target_pull_requests.append(pull)
        # target_pull_requests_count += 1

        target_pull_requests.append(pull)

    return target_pull_requests


def _get_pull_requests_tags(repo):
    pull_requests_tags = ""
    target_pull_request_cnt = 0
    for pull in _get_target_pull_requests(repo):
        if "PROR-" not in pull.title and "INT-" not in pull.title:
            continue

        if len(pull_requests_tags) > 0 :
            pull_requests_tags += "\n"

        pull_requests_tags += f"> <{_make_pr_link_with_no(repo.clone_url, pull.number)}|{pull.title}>"
        target_pull_request_cnt += 1

        # if pull.labels == []:
        #     # D-5 Setting up labels
        #     pull.set_labels("D-5")
        #     pr_msg_to_slack += f"> <{pr_link}|[ D-5 ] {pull.title }>" + "\n"
        # elif pull.get_labels()[0].name == "D-0":
        #     # For D-0 labels
        #     pr_msg_to_slack += f"> <{pr_link}|[ D-0 ] {pull.title }>" + "\n"
        # else:
        #     # If there is a non-D-0 label, set the tag to one less day.
        #     before_label = pull.get_labels()[0].name
        #     after_label = _set_label_decrease(pull, before_label)
        #     pr_msg_to_slack += (
        #         f"> <{pr_link}|[ {after_label} ] {pull.title }>" + "\n"
        #     )

    if target_pull_request_cnt > 0:
        return target_pull_request_cnt, pull_requests_tags
    else:
        return 0, str()


def send_pull_request_reminder(slack_notification_on: bool ,private_access_token: str, repo_name_list, slack_webhook_url: str):

    git_api_client = Github(private_access_token)

    target_pull_requests_tags = []
    total_target_pull_request_cnt = 0

    for repo_name in repo_name_list:
        repo = git_api_client.get_repo(repo_name)
        target_pull_request_cnt, pull_requests_tags = _get_pull_requests_tags(repo)

        if pull_requests_tags :
            target_pull_requests_tags.append(pull_requests_tags)
            total_target_pull_request_cnt = total_target_pull_request_cnt + target_pull_request_cnt

    if len(target_pull_requests_tags) > 0 :
        pull_request_msg_head_to_slack = (
            f"<!here> 👋🏻 총 {total_target_pull_request_cnt}개의 Pull Request가 리뷰를 기다 리고 있어요! :revolving_hearts:\n"
        )
        pull_request_msg_to_slack = pull_request_msg_head_to_slack + "\n\n".join(target_pull_requests_tags)
        print(f'pull_request_msg_to_slack = {pull_request_msg_to_slack}')
        if slack_notification_on:
            # print(f'pull_request_msg_to_slack = {pull_request_msg_to_slack}')
            _send_slack(slack_webhook_url, pull_request_msg_to_slack)


@click.command(help="""
    pull request reminder
""")
@click.option(
    "--slack-notification",
    "-n",
    type=str,
    help="""
        Whether to send slack notifications\n"
        on: sent, off: unsent
    """
)
def main(slack_notification: Optional[str]):

    slack_notification_on = False

    if slack_notification is not None:
        if slack_notification == "on":
            slack_notification_on = True
    else:
        if config['slack_notification'] == "on":
            slack_notification_on = True

    print(f'slack notification: {slack_notification_on}')

    for repo in config['repo_list']:
        send_pull_request_reminder(slack_notification_on, repo[0], repo[1], repo[2])


if __name__ == '__main__':
    main()
