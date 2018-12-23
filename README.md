# Slack Standup Snitch

![snitch_bot_in_action](https://cloud.githubusercontent.com/assets/8029092/7402900/f85095c0-ee95-11e4-91e7-940717732f3b.jpg)

The Slack Standup Snitch is a [Slack](https://slack.com/) bot that
counts the unique days that each user was active on a specified
channel and calls out the inactive users. It runs on Python 3 without
any further dependencies. It does the timestamp math to grab the posts
from Slack between midnight the previous night and n days before
that. It aggregates the *unique* days - if you posted five times on
Monday and once on Wednesday, that counts for two days. It returns a
text histogram of the activity and "ats" the users who checked in zero
times.

## Setup instructions

1. Clone this repo.
2. [Get a Slack API token.](https://api.slack.com/web) Save it to the
   repo's directory under `api_token.txt`. (You can save it wherever
   you want, but the `.gitignore` is put together to make this a
   convenient choice. The same is true for the other filenames below.)
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

## How to use

### Typical use

```
python3 standup_snitch.py -t api_token.txt \
                          -i input_channel.csv \
                          -o output_channel.csv \
                          -u users.csv \
                          -b SnitchBot
```

### Other features

* `-r`: Dry-run the `standup_snitch` report to standard output instead
of sending it to Slack.
