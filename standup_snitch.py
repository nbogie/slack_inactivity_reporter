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
import enum
import slack_api
import csv
import argparse
import json
from collections import Counter
import itertools
import datetime as DT
import os


class MissingEnvVarException(Exception):
   """Raised when a required env var is not set"""
   pass

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
    
    if 'has_more' in history_raw and history_raw['has_more']:
        print('WARNING: messages missing from this report.  Try reducing the number of days to report upon.')

    return (history_raw, 
            [{'user': message['user'], 'ts': message['ts']}
            for message in history_raw['messages']
            if (message['type'] == 'message' and
                'user' in message and
                'ts' in message)])

def find_calls_activity(history_raw, users):
    all_calls = [{
        'user': message['user'], 
        'ts': message['ts'], 
        'name': message['room']['name'],
        'date_start': message['room']['date_start'],
        'duration_m': round((int(message['room']['date_end']) - int(message['room']['date_start'])) / 60),
        'participants': message['room']['participant_history']} 
    for message in history_raw['messages']
    if 'subtype' in message
        and message['subtype'] == 'sh_room_created' 
        and message['text'].startswith('Started a ')
        and 'user' in message 
        and 'ts' in message
        and 'room' in message]
    return [c for c in all_calls if c['duration_m'] > 0 ]

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
    return "Slack report time: %s\n\nLeast activity (posts, replies) over the last %d days on #%s\n" % ( DT.datetime.now().strftime("%c"), n_days, channel_name )

class ReportMode(enum.Enum):
    FULL = 1
    LITE = 2

def make_activity_report(active_users_dict, users, n_days, mode=ReportMode.LITE):
    
    if (mode == ReportMode.LITE):
        title = "Total posts per user in %d days" % n_days
        header = ""
        spacer = ""

    else:
        title = "More detail: Msgs-per-day breakdown"
        header = "USER / DAY:     %s days ago" % ("".join(["%2d " % day_offset for day_offset in range(1, n_days + 1)]))
        spacer ="-" * 50
    
    res = []
    res.append("\n%s:\n" % title)
    res.append(header)
    res.append(spacer)
    
    for uid in sorted(active_users_dict, key=lambda k: (sum(active_users_dict[k].values()), -min(active_users_dict[k], default=99))):
        nameCol = users[uid]['real_name'].ljust(10)
        countTotal = sum(active_users_dict[uid].values())
        count_strs = "".join(["%2s " % active_users_dict[uid].get(day_offset, 0) for day_offset in range(n_days)])
        if mode == ReportMode.LITE:
            res.append("%s(%3d)" % (nameCol, countTotal))
        else:
            res.append("%s(%3d) %s" % (nameCol, countTotal, count_strs))

    return "\n".join(res)


def make_call_summary_report(calls_list, users, for_graphviz=False):
    lines = ["", "Calls Summary - Who talks to whom?", ""]
    summary_of_each_call = [
            (users[call['user']]['real_name'], 
            call['duration_m'],
            [users[participant]['real_name'] for participant in call['participants'] if participant in users]
            )         
        for call in calls_list if call['user'] in users]
    
    if for_graphviz:
        # list each user as node
        # list each call as a list of edges between its participants
        lines = ["graph CallNetwork {"]
        for uid in users:
            lines.append("%s;" % users[uid]['real_name'])
        for (_, _, participants) in summary_of_each_call:            
            for (f, t) in itertools.combinations(participants, 2):
                lines.append("%s -- %s;" % (f, t))
        
        lines.append("}")         

    else:
        for (starter, duration, participants) in summary_of_each_call:
            lines.append("Call of duration %dm started by %s, \n\twith participants %s" 
            % (duration, starter, ", ".join(participants)))    

    return "\n".join(lines)

def make_calls_activity_report(active_users_dict, calls_history, users, initiators_only = False):
    
    if initiators_only:
        title = "CALL INITIATION"
        header = "Number of calls the user INITIATED"
    else:
        title = "CALL PARTICIPATION"
        header = "Number of calls the user participated in.  Note: Durations may not reflect the amount of time the participant spent on the call."
    spacer = ""

    res = []
    res.append("\n%s:\n" % title)
    res.append(header)
    res.append(spacer)
    
    for uid in sorted(active_users_dict, key=lambda k: (-len([c for c in calls_history if c['user'] == k or (k in c['participants'] and not initiators_only)]))):
        nameCol = users[uid]['real_name'].ljust(10)
        durations = [c['duration_m'] for c in calls_history 
        if c['user'] == uid or (uid in c['participants'] and not initiators_only)]
        totalCalls = len(durations)
        res.append("%s %3d calls  (%s minutes)" % (nameCol, totalCalls, durations))
        
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
    parser.add_argument('-d', '--num_days', default=5, type=int, help = 'number of days over which to look back')
    parser.add_argument('-l', '--log_raw_json', action='store_true', help = 'log raw json response to file: sensitive/channels.history.json')
    parser.add_argument('-g', '--graph_calls', action='store_true', help = 'graph calls to dot file: sensitive/calls.dot')
    parser.add_argument('-f', '--use_fake_data', action='store_true', help = 'use fake data instead of getting from slack API')
    parser.add_argument('-r', '--dry_run', action = 'store_true',
                        help = 'flag to dry-run results to standard output')
    return parser.parse_args()

def get_env_var_or_fail(k):
    if k in os.environ:
        return os.environ[k]
    else:
        raise MissingEnvVarException('Missing required env var %s' % k)

def env_var_to_dict(env_var_name, field_names):
    raw_val = get_env_var_or_fail(env_var_name)
    return dict(zip(field_names, raw_val.split(",")))
    

def env_var_to_dict_of_dicts(env_var_name, field_names, key_field_name, line_sep):
    """Take an env var with content like:
       a1,a2,a3/b1,b2,b3/c1,c2,c3
       and convert into a dict with a subdict for each line.
       The subdicts map the given field names to the corresponingly-ordered value
       They are stored in the main dict by the value they have for key_field_name
    """
    dicts = {}
    raw_val = get_env_var_or_fail(env_var_name)
    for line in raw_val.split(line_sep):
        if len(line) < 4:
            raise Exception("empty line in env var: %s" % env_var_name)
        d  = dict(zip(field_names, line.split(",")))
        dicts[d[key_field_name]] = d
    return dicts

def read_env_vars():
    token = get_env_var_or_fail("SLACK_API_TOKEN")    
    input_channel = env_var_to_dict("SLACK_INPUT_CHANNEL", ['channel_id', 'channel_name'])
    output_channel = env_var_to_dict("SLACK_OUTPUT_CHANNEL", ['channel_id', 'channel_name'])
    users_dict = env_var_to_dict_of_dicts("SLACK_USERS", ["user_id", "user_name","real_name"], "user_id", "/")
    return token, input_channel, output_channel, users_dict

#not used any more now we're moving to env vars for aws lambda
def retired_read_config_files(args):
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
    token, input_channel, output_channel, users = read_env_vars() # read_config_files(args)
    should_graph_calls = args.graph_calls
    now_datetime = DT.datetime.now()
    min_posts = 1
    # Slack API call to get history
    history_raw, message_history = get_message_history(token,
                                          input_channel['channel_id'],
                                          input_channel['channel_name'],
                                          n_days,
                                          now_datetime,
                                          args.use_fake_data,
                                          args.log_raw_json)
    
    #calc who is active
    active_users_dict = aggregate_activity(message_history, n_days, now_datetime, users)
    
    calls_list = find_calls_activity(history_raw, users)
    
    # Preamble
    introduction = make_introduction(input_channel, n_days)

    counter = Counter(map(lambda x: x['user'], message_history))

    report1 = make_activity_report(active_users_dict, users, n_days, mode=ReportMode.LITE)
    report2 = make_activity_report(active_users_dict, users, n_days, mode=ReportMode.FULL)
    calls_summary_report = make_call_summary_report(calls_list, users)
    if should_graph_calls:
        graphviz_calls_summary_report = make_call_summary_report(calls_list, users, for_graphviz=True)
        with open('sensitive/calls.dot', 'w') as f:
            f.write(graphviz_calls_summary_report)
    
    calls_report = make_calls_activity_report(active_users_dict, calls_list, users)
    call_starters_report = make_calls_activity_report(active_users_dict, calls_list, users, initiators_only=True)
    
    # Assemble the full_message
    full_message = '\n'.join(['```', introduction, report1, report2, calls_summary_report, calls_report, call_starters_report, '```'])

    # Slack API call to publish summary
    if dry_run:
        print(full_message)
    else:
        print(full_message)
        # we don't want to post to slack at all, currently. or maybe into mentors channel.
        # post_message(token, output_channel['channel_id'], full_message)

run()
