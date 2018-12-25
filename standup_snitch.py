#! /usr/bin/env python3

# Using the Slack API:
# (1) Get recent history of a specified input channel.
# (2) For each known user, note if user posted any message to the channel.
# (3) Post a report to stdout (or to a specified output slack channel, 
#    calling out the inactive users.
#
# Usage: python3 standup_snitch.py -t api_token.txt \
#                                  -i input_channel.csv \
#                                  -o output_channel.csv \
#                                  -u users.csv \
#                                  -d 7

from random import randint

import slack_api
import csv
import argparse
import json
from collections import Counter
import datetime as DT


def format_channel_for_slack(channel_dict):
    return ''.join(['<#',
                    channel_dict['channel_id'],
                    '|',
                    channel_dict['channel_name'],
                    '>'])


def format_user_for_slack(user_id, user_info):
    return ''.join(['<@',
                    user_id,
                    '|',
                    user_info['user_name'],
                    '>'])


def format_user_for_text(user_id, user_info):
    return "%s (%s)" % (user_info['real_name'], user_info['user_name'])


def json_pp(obj):
    return json.dumps(obj, indent=4, sort_keys=True)


def get_message_history(token, channel_id, channel_name, days, now_datetime, use_fake_data=False, should_log_raw_channel_history=False):
    ts = timestamp_for_days_ago(now_datetime, days)
    if (use_fake_data):      
        print('using fake data, not loaing from slack')          
        with open('sensitive/channels.history.json') as f:
            history_raw = json.load(f)
    else:
        history_raw = slack_api.call_slack('channels.history',
                                           {'token': token,
                                            'channel': channel_id, 
                                            'oldest': ts,
                                            'count': 1000}) # 1000 messages is the maximum allowed by the API.    

    if (should_log_raw_channel_history):
        with open('sensitive/channels.history.json', 'w') as f:
            f.write(json_pp(history_raw))    
    return [{'user': message['user'], 'ts': message['ts']}
            for message in history_raw['messages']
            if (message['type'] == 'message' and
                'user' in message and
                'ts' in message)]


def get_day_offset_for_ts(ts, now_datetime):
    now_ts = (now_datetime - DT.datetime(1970, 1, 1)) / DT.timedelta(seconds=1)
    days_ago = int((now_ts - ts) / 86400)
    return days_ago
    

def aggregate_activity(history, n_days, now_datetime, users):
    user_activity_dict = {}
    
    for user_id in users:        
        user_activity_dict[user_id] = Counter()
        
    for message in history:
        try:
            user = message['user']
            day_offset = get_day_offset_for_ts(float(message['ts']), now_datetime)
            user_activity_dict[user][day_offset] += 1
        except KeyError:
            # Post from someone we're not tracking
            pass
    return user_activity_dict


def make_introduction(input_channel, n_days):
    channel_name = input_channel['channel_name']
    return "Slack report time: %s\n\nWho's NOT present in the last %d days on #%s?\n" % ( DT.datetime.now(), n_days, channel_name )


def make_conclusion(active_users_dict, n_days, counter, threshold, users):
    res = []
    non_posters = [user_id for user_id in active_users_dict
                   if sum(active_users_dict[user_id].values()) < threshold]
    if len(non_posters) == 0:
        res.append('No-one is missing!  Go team!')
    else:
        tag_items = [format_user_for_text(user_id, users[user_id])
                     for user_id in non_posters]
        res.extend(tag_items)
    
    res.append("\nMSGS-PER-DAY BREAKDOWN:\n")
    #header
    res.append("USER / DAY:     %s" % ("".join(["%2d " % day_offset for day_offset in range(1, n_days + 1)])))
    res.append("-" * 80)
    
    for uid in sorted(active_users_dict, key=lambda k: (sum(active_users_dict[k].values()), -min(active_users_dict[k], default=99))):
        count_strs = "".join(["%2s " % active_users_dict[uid].get(day_offset, 0) for day_offset in range(n_days)])
        res.append("%10s(%3d) %s" % (users[uid]['real_name'], sum(active_users_dict[uid].values()), count_strs))

    return "\n".join(res)


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
    parser.add_argument('-d', '--num_days', default=10, type=int, help = 'number of days over which to look back')
    parser.add_argument('-l', '--log_raw_json', action='store_true', help = 'log raw json response to file: sensitive/channels.history.json')
    parser.add_argument('-f', '--use_fake_data', action='store_true', help = 'use fake data instead of getting from slack API')
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
        users = {user['user_id']: {'user_name': user['user_name'], 
                                   'real_name': user['real_name'], 
                                   'user_id': user['user_id']} for user in csv.DictReader(user_file)}
    return token, input_channel, output_channel, users                      


def timestamp_for_days_ago(now_datetime, n_days):
    # no doubt there's a tidier way to do this.  Newbie code.
    week_ago = now_datetime - DT.timedelta(days=n_days)
    timestamp = (week_ago - DT.datetime(1970, 1, 1)) / DT.timedelta(seconds=1)
    return timestamp


def run():
    args = parse_command_line()
    dry_run = args.dry_run
    n_days = int(args.num_days)
    token, input_channel, output_channel, users = read_config_files(args)
    now_datetime = DT.datetime.now()
    min_posts = 1
    # Slack API call to get history
    message_history = get_message_history(token,
                                          input_channel['channel_id'],
                                          input_channel['channel_name'],
                                          n_days,
                                          now_datetime,
                                          args.use_fake_data,
                                          args.log_raw_json)
    
    #calc who is active
    active_users_dict = aggregate_activity(message_history, n_days, now_datetime, users)

    # Preamble
    introduction = make_introduction(input_channel, n_days)

    counter = Counter(map(lambda x: x['user'], message_history))
    
    conclusion = make_conclusion(active_users_dict, n_days, counter, min_posts, users)

    # Assemble the full_message
    full_message = '\n'.join(['```', introduction, conclusion, '```'])

    # Slack API call to publish summary
    if dry_run:
        print(full_message)
    else:
        print(full_message)
        # we don't want to post to slack at all, currently. or maybe into mentors channel.
        # post_message(token, output_channel['channel_id'], full_message)

run()
