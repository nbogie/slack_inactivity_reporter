# Slack Inactivity Reporter

This is a modification (primarily a simplification) of an existing project "Standup Snitch", for our purposes.

It is a script that uses the [Slack](https://slack.com/) API and reports user activity to stdout.  The project also has the ability to post the report back to a different slack channel.

It runs fully automated so could be scheduled with cron.

## Setup instructions

1. Clone this repo.
2. [Get a LEGACY Slack API token.](https://api.slack.com/custom-integrations/legacy-tokens) Be very careful with this key, do NOT check it into source control.  If someone has this token, they have access to any slack content you can read 
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
   will be saved here for debugging if you request them.  
   This directory is ignored by git.

6. Make your slack legacy token available as an environment variable called SLACK_API_TOKEN.  The script will pick it up when it runs.

## How to use

### Typical usage:

Make an executable script with this content (but with your input data):

```
export SLACK_USERS=UHAAABB123,neill,Neill/UHYAABB122,german,German/...more users here.../UABB124,last-user/LastUserExample

SLACK_OUTPUT_CHANNEL=exampleid,random SLACK_INPUT_CHANNEL=YOURCHANNELID,your-channel-name python3 standup_snitch.py -d7 -g
```
Then run it.


### Other features

* `-r`: Dry-run the `standup_snitch` report to standard output instead
of sending it to Slack.
* `-f`: Use fake (non-live) data read from filesystem  `sensitive/channels.history.json`
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

USER / DAY:      1  2  3  4  5  6  7 
--------------------------------------------------------------------------------
       Ali(  0)  0  0  0  0  0  0  0 
     Aaron(  0)  0  0  0  0  0  0  0 
      Mary(  0)  0  0  0  0  0  0  0 
  Marshall(  0)  0  0  0  0  0  0  0 
       Sol(  0)  0  0  0  0  0  0  0 
     Norah(  1)  0  0  0  0  0  1  0 
    Sevrin(  1)  0  0  0  0  0  1  0 
     Allan(  1)  0  0  0  0  1  0  0 
     Jonny(  1)  0  0  1  0  0  0  0 
    Edward(  1)  0  1  0  0  0  0  0 
      Bill(  2)  0  0  0  0  1  0  1 
     Kelly(  2)  0  0  0  1  0  1  0 
  Slackbot(  2)  0  1  0  0  0  0  1 
     David(  3)  0  0  0  0  1  2  0 
    Marvin(  3)  0  0  0  1  2  0  0 
     Neill(  3)  0  1  0  0  0  0  2 
    German(  3)  1  0  0  0  0  1  1 
       Ant(  4)  0  0  0  0  0  0  4 
     Niala(  4)  0  0  0  0  0  1  3 
    Marvel(  4)  0  0  2  0  0  0  2 
    Misael(  4)  0  0  1  0  1  2  0 
     Ivana(  6)  0  2  0  0  1  2  1 
    Indigo(  7)  0  0  0  0  1  4  2 
      Tony(  7)  0  2  2  0  1  2  0 
      Easy(  8)  0  0  1  1  0  0  6 
      Zeke(  8)  1  3  1  0  3  0  0 
      Adam(  9)  0  0  0  1  3  5  0 
     Molly(  9)  0  1  0  0  0  1  7 
       Jen(  9)  0  4  1  0  0  4  0 
     Maisy( 19)  0  0  2  2  0  0 15 
      Conn( 21)  0  0  2  0  0  3 16 


Who's NOT present in the last 7 days on #student-channel?

Ali (ali), 
Aaron (aabb), 
Mary (mary2020), 
Marshall (marshall), 
Sol (s.a)
```
