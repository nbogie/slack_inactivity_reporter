#! /usr/bin/env python3

# Using the Slack API:
# (1) Get recent history (last 1000 messages) of a specified input channel.
# (2) For each known user, note if user posted any message to the channel.
# (3) Post a report to a specified output channel, calling out the
#     inactive users.
#
# Usage: python3 standup_snitch.py -t api_token.txt \
#                                  -i input_channel.csv \
#                                  -o output_channel.csv \
#                                  -u users.csv \
#                                  -b SnitchBot

import slack_api
import csv
import argparse
import json
from collections import Counter
import datetime as DT

def format_channel(channel_dict):
    return ''.join(['<#',
                    channel_dict['channel_id'],
                    '|',
                    channel_dict['channel_name'],
                    '>'])

def format_user(user_id, user_name):
    return ''.join(['<@',
                    user_id,
                    '|',
                    user_name,
                    '>'])

def json_pp(obj):
    return json.dumps(obj, indent=4, sort_keys=True)
    
def get_message_history(token, channel, days):
    # 1000 messages is the maximum allowed by the API.
    ts = timestamp_for_days_ago(days)
    print("channel", channel, " for ", days, " days.  TS: ", ts)
    history_raw = slack_api.call_slack('channels.history',
                                       {'token': token,
                                        'channel': channel, 
                                        'oldest': ts,
                                        'count': 1000})
    print(json_pp(history_raw))

    return [{'user': message['user'], 'ts': message['ts']}
            for message in history_raw['messages']
            if (message['type'] == 'message' and
                'user' in message and
                'ts' in message)]

def aggregate_activity(history, users):
    user_activity_dict = {}
    for user_id in users:
        user_activity_dict[user_id] \
            = False

    for message in history:
        try:
            user = message['user']
            user_activity_dict[user] = True
        except KeyError:
            # Post from someone we're not tracking
            pass
    print(user_activity_dict)
    return user_activity_dict

def make_introduction(input_channel, n_days):
    return "Who's not present in the last %d days on %s?" % ( n_days, format_channel(input_channel) )

def make_conclusion(active_users, users):
    non_posters = [user_id for user_id in active_users
                   if active_users[user_id] == False]

    if len(non_posters) == 0:
        return 'Go team!'
    else:
        tag_items = [format_user(user_id, users[user_id])
                     for user_id in non_posters] + ['we miss you.']
        return ', '.join(tag_items)

def post_message(token, channel, text, bot_name):
    raise Exception("TRIED TO POST A MESSAGE TO SLACK!")
    slack_api.call_slack('chat.postMessage',
                         {'token': token,
                          'channel': channel,
                          'text': text,
                          'username': bot_name})

def parse_command_line():
    # Command line flags
    parser = argparse.ArgumentParser()
    parser.add_argument('-t', '--token_file', help = 'file with API token')
    parser.add_argument('-i', '--input_channel_file',
                        help = 'file with Slack channel to monitor')
    parser.add_argument('-o', '--output_channel_file',
                        help = 'file with Slack channel to write to')
    parser.add_argument('-u', '--user_file', help = 'file with user list')
    parser.add_argument('-d', '--num_days', action="store", default=10, type=int, help = 'number of days over which to look back')
    parser.add_argument('-b', '--bot_name', help = 'display name of bot')
    parser.add_argument('-r', '--dry_run', action = 'store_true',
                        help = 'flag to dry-run results to standard output')
    return parser.parse_args()


def read_config_files(args):
    # Read configuration from the specified files
    with open(args.token_file) as token_file:
        token = token_file.read().strip()

    with open(args.input_channel_file) as input_channel_file:
        # Take only the first line after the header
        input_channel = next(csv.DictReader(input_channel_file))

    with open(args.output_channel_file) as output_channel_file:
        # Take only the first line after the header
        output_channel = next(csv.DictReader(output_channel_file))

    with open(args.user_file) as user_file:
        users = {user['user_id']: user['user_name']
                 for user in csv.DictReader(user_file)}
    return token, input_channel, output_channel, users                      

def timestamp_for_days_ago(n_days):
    # no doubt there's a tidier way to do this.  Newbie code.
    now = DT.datetime.now()
    week_ago = now - DT.timedelta(days=n_days)
    timestamp = (week_ago - DT.datetime(1970, 1, 1)) / DT.timedelta(seconds=1)
    return timestamp

def run():
    args = parse_command_line()
    bot_name = args.bot_name
    dry_run = args.dry_run
    n_days = int(args.num_days)

    token, input_channel, output_channel, users = read_config_files(args)

    # Slack API call to get history
    message_history = get_message_history(token,
                                          input_channel['channel_id'],
                                          100)
    print(json_pp(message_history))

    counter = Counter(map(lambda x: x['user'], message_history))
    
    print([(users[e[0]], e[1]) for e in counter.most_common() if e[0] in users])
    
    #calc who is active
    active_users = aggregate_activity(message_history, users)

    # Preamble
    introduction = make_introduction(input_channel, n_days)

    # Call out non-posters or congratulate the team
    conclusion = make_conclusion(active_users, users)

    # Assemble the full_message
    full_message = '\n'.join([introduction, conclusion])

    # Slack API call to publish summary
    if dry_run:
        print(full_message)
    else:
        print(full_message)
        # we don't want to post to slack at all, currently. or maybe into mentors channel.
        # post_message(token, output_channel['channel_id'], full_message, bot_name)

print(timestamp_for_days_ago(7))
run()
