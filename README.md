# Slack Standup Snitch

This is a modification (primarily a simplification) of an existing project, for our purposes.

The Slack Standup Snitch is a script that uses the [Slack](https://slack.com/) API and reports user activity to stdout.  The project also has the ability to post the report back to a different slack channel.

The original made a report that looked like this:
![snitch_bot_in_action](https://cloud.githubusercontent.com/assets/8029092/7402900/f85095c0-ee95-11e4-91e7-940717732f3b.jpg)

It runs fully automated so could be scheduled with cron.

## Setup instructions

1. Clone this repo.
2. [Get a LEGACY Slack API token.](https://api.slack.com/custom-integrations/legacy-tokens) Save it to the
   repo's directory under `api_token.txt`. (You can save it wherever
   you want, but the `.gitignore` is put together to make this a
   convenient choice. The same is true for the other filenames below.)
   We'll improve this to use the new auth system if we decide to 
   use it at all.
3. Get a list of your users along with their internal Slack IDs:

   ```
   python3 list_users.py < api_token.txt > users.csv
   ```

   Typically you'll manually edit `users.csv` to pare the list down to
   the active people you want to monitor.
4. Get a list of your channels along with their internal Slack IDs:

   ```
   python3 list_channels.py < api_token.txt > input_channel.csv
   cp input_channel.csv output_channel.csv
   ```

   Manually remove all but two lines from each file:
   `input_channel.csv` should have a header and the line for the
   channel you want to monitor. Similarly, `output_channel.csv` should
   have a header and the line for the channel you want to send the
   report to.

5. make a directory called `sensitive` Logs of the API json responses 
   will be saved here for debugging.  This directory is ignored by git.

## How to use

### Typical use

```
python3 standup_snitch.py -t api_token.txt \
                          -i input_channel.csv \
                          -o output_channel.csv \
                          -u users.csv \
                          -d 5
```

### Other features

* `-r`: Dry-run the `standup_snitch` report to standard output instead
of sending it to Slack.

## On the Slack API usage:

The following calls are used:

* [channels.list](https://api.slack.com/methods/channels.list)
* [users.list](https://api.slack.com/methods/users.list)
* [channels.history](https://api.slack.com/methods/channels.history)
* [chat.postMessage](https://api.slack.com/methods/chat.postMessage) (removed from cyf impl, currently)

Unix (epoch) Timestamps are used.  See: https://api.slack.com/docs/message-formatting

## Development and Debugging:

The script will log the json of the channels.history API call in sensitive/channels.history.json
This contains other messages (currently filtered from final report) which will be useful to use (e.g. calls)

# ToDo

See the github project's issue tracker.

Also, Jonny suggested some KPIs

* Amount of messages
* Regularity of messages
* Time on calls
* Speaking-time on calls??

# Sample output

```
Looking at history of channel student-channel (ABCD6ABCD) for 7 days.  Oldest timestamp requested: 1545050402.533997

MOST ACTIVE:
Charlie: 21
Morris: 19
Jane: 9
Mary: 9
Alan: 9
Zeke: 8
Edward: 8
Tom: 7
Isaac: 7
Neill: 6
Ian: 6
Maisy: 4
Molly: 4
Norah: 4
Abraham: 4
Graham: 3
Mike: 3
Doris: 3
Slackbot: 2
Kev: 2
Billy: 2
Ed: 1
Joker: 1
Alfred: 1
Susan: 1
Nelly: 1



Who's NOT present in the last 7 days on #student-channel?

Ali (ali), 
Horace (horace.spiders), 
Hopper (hopper), 
Will (will), 
Mike (dm)
```