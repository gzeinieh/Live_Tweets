#!/usr/bin/env python
import datetime
import flask
import redis
import time
import json
import tweepy
from tweepy import Stream
from tweepy.streaming import StreamListener



app = flask.Flask(__name__)
app.secret_key = 'xxxxxxx'
red = redis.StrictRedis()


def event_stream():
    pubsub = red.pubsub()
    pubsub.subscribe('live')
    for message in pubsub.listen():
        print(message)
        yield 'data: %s\n\n' % message['data']


@app.route('/post', methods=['POST'])
def post():
    message = flask.request.form['message']
    red.publish('live', u'LISTENING TO TWEETS ABOUT %s' % message)
    call_twitter(message, 1)
    red.publish('live', u'DONE')
    red.publish('live', u'DONE')
    red.publish('live', u'DONE')
    return flask.Response(status=204)




@app.route('/stream')
def stream():
    return flask.Response(event_stream(),
                          mimetype="text/event-stream")


@app.route('/')
def home():
    return """
        <!doctype html>
        <title>live</title>
        <script src="http://ajax.googleapis.com/ajax/libs/jquery/1.7.1/jquery.min.js"></script>
        <style>body { max-width: 500px; margin: auto; padding: 1em; background: #00aced; color: #fff; font: 16px/1.6 menlo, monospace; }</style>
        <p><b>Live Tweets</b></p>
        <p>search: <input id="in" /></p>
        <pre id="out"></pre>
        <script>
            function sse() {
                var source = new EventSource('/stream');
                var out = document.getElementById('out');
                source.onmessage = function(e) {
                    // XSS in chat is fun
                    out.innerHTML =  e.data + '\\n' + out.innerHTML;
                };
            }
            $('#in').keyup(function(e){
                if (e.keyCode == 13) {
                    $.post('/post', {'message': $(this).val()});
                    $(this).val('');
                }
            });
            sse();
        </script>
    """

#############################
######### TWitter ###########
#############################


######### auth ##############

class TwitterAuth():

    def __init__(self, CONSUMER_KEY,CONSUMER_SECRET, ACCESS_KEY, ACCESS_SECRET):
        self.CONSUMER_KEY = CONSUMER_KEY
        self.CONSUMER_SECRET = CONSUMER_SECRET
        self.ACCESS_KEY = ACCESS_KEY
        self.ACCESS_SECRET = ACCESS_SECRET
        self.auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        self.auth.set_access_token(ACCESS_KEY, ACCESS_SECRET)
        self.api = tweepy.API(self.auth)


T = TwitterAuth('xxxxx', 'xxxxxxxxxxxx', 'xxxxxxxxxxx', 'xxxxxxxxxx')

auth = T.auth

############ Listener ###########

class Listener(StreamListener):

    def __init__(self, time_limit):
        """

        :param filter_by: the word to search for
        :param time_limit: the duration of the streaming
        """
        super().__init__()
        self.time_limit = time_limit * 60
        self.start_time = time.time()

    def on_data(self, data):
        """

        :param data: data from twitter api
        :return: process data and push it to redis
        """
        if (time.time() - self.start_time) < self.time_limit:

            all_data = json.loads(data)

            tweet = all_data["text"]

            user = all_data["user"]["screen_name"]

            now = datetime.datetime.now().replace(microsecond=0).time()
            red.publish('live', u'[%s] %s: %s' % (now.isoformat(), user, tweet))

            return True

        else:
            return False

    def on_error(self, status):
        """

        :param status: error
        :return: deal with twitter 420 api error (420: when making many wrong streaming api requests)
        """
        if status == 420:
            print(status)
            return False


def call_twitter(word,time_limit):
    twitterStream = Stream(auth, Listener(time_limit))
    twitterStream.filter(track=[word])


##############


if __name__ == '__main__':
    app.debug = True
    app.run()


