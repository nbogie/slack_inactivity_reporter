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

def get_message_history(token, channel):
    # 1000 messages is the maximum allowed by the API.
    print("channel", channel)
    history_raw = slack_api.call_slack('channels.history',
                                       {'token': token,
                                        'channel': channel,                                       
                                        'count': 1000})
    print(history_raw)

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

def introduction(input_channel):
    fmt_string = "Who's not present in the last 1000 messages on {:s}?"
    return fmt_string.format(format_channel(input_channel))

def conclusion(active_users, users):
    non_posters = [user_id for user_id in active_users
                   if active_users[user_id] == False]

    if len(non_posters) == 0:
        return 'Go team!'
    else:
        tag_items = [format_user(user_id, users[user_id])
                     for user_id in non_posters] + ['we miss you.']
        return ', '.join(tag_items)

def post_message(token, channel, text, bot_name):
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
    parser.add_argument('-b', '--bot_name', help = 'display name of bot')
    parser.add_argument('-r', '--dry_run', action = 'store_true',
                        help = 'flag to dry-run results to standard output')
    return parser.parse_args()

args = parse_command_line()
bot_name = args.bot_name
dry_run = args.dry_run

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

# Slack API call to get history
message_history = get_message_history(token,
                                      input_channel['channel_id'])
print (message_history)
#calc who is active
active_users = aggregate_activity(message_history, users)
print (active_users)

# Preamble
introduction = introduction(input_channel)

# Call out non-posters or congratulate the team
conclusion = conclusion(active_users, users)

# Assemble the full_message
full_message = '\n'.join([introduction,
                          
                          conclusion])

# Slack API call to publish summary
if dry_run:
    print(full_message)
else:
    post_message(token, output_channel['channel_id'], full_message, bot_name)
