#!/usr/bin/python2.6
# coding=utf-8

# Copyright (c) 2011 Tim Foster
#
# Portions:
# Copyright 2007 The Python-Twitter Developers

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


# Twitter integration for feedplus, using python-twitter

import ConfigParser
import os
import sys
import urllib2
from urlparse import parse_qsl

import oauth2
import twitter

import settings

def get_consumer_key():
        """This is entirely questionable.  See settings.py"""
        consumer_key = None

        try:
                loc = "%s/consumer_key.txt" % settings.TWITTER_CONSUMER_URL
                url = urllib2.urlopen(loc)
                consumer_key = url.read().rstrip()
        except (urllib2.HTTPError, IOError), e:
                print "Unable to obtain consumer_key from %s: %s" % (loc, e)
        return consumer_key

def get_consumer_secret():
        """This is entirely questionable.  See settings.py"""
        consumer_secret = None
        try:
                loc = "%s/consumer_secret.txt" % settings.TWITTER_CONSUMER_URL
                url = urllib2.urlopen(loc)
                consumer_secret = url.read().rstrip()
        except (urllib2.HTTPError, IOError), e:
                print "Unable to obtain consumer_secret from %s: %s" % (loc, e)
        return consumer_secret

def get_access_tokens(consumer_key, consumer_secret):
        """This code is largely lifted from get_access_token.py from the
        python-twitter project.  It now caches the key and secret in a
        _highly secure_ manner in the users' home directory, rather than
        asking the user for authorisation each time."""

        config = None
        config_path = os.path.expanduser("~/.feedplusrc")
        if os.path.exists(config_path):
                config = ConfigParser.ConfigParser()
                config.read([config_path])
                oauth_token = None
                oauth_token_secret = None
                try:
                        oauth_token = config.get("feedplus", "oauth_token")
                        oauth_token_secret = config.get("feedplus",
                            "oauth_token_secret")
                except ConfigParser.NoOptionError:
                        pass
                if oauth_token and oauth_token_secret:
                        return oauth_token, oauth_token_secret
        else:
                config = ConfigParser.ConfigParser()
                config.add_section("feedplus")

        REQUEST_TOKEN_URL = "https://api.twitter.com/oauth/request_token"
        ACCESS_TOKEN_URL  = 'https://api.twitter.com/oauth/access_token'
        AUTHORIZATION_URL = 'https://api.twitter.com/oauth/authorize'
        SIGNIN_URL        = 'https://api.twitter.com/oauth/authenticate'

        if consumer_key is None or consumer_secret is None:
                print ("We require a consumer_key and a consumer_secret."
                    "\nThese can be acquired by registering a dummy "
                    "'application' with Twitter, see https://dev.twitter.com")
                sys.exit(1)

        signature_method_hmac_sha1 = oauth2.SignatureMethod_HMAC_SHA1()
        oauth_consumer = oauth2.Consumer(key=consumer_key,
            secret=consumer_secret)
        oauth_client = oauth2.Client(oauth_consumer)

        print "Requesting temp token from Twitter."

        resp, content = oauth_client.request(REQUEST_TOKEN_URL, 'GET')

        if resp["status"] != '200':
                print ("Invalid respond from Twitter requesting temp "
                    "token: %s" % resp["status"])
        else:
                request_token = dict(parse_qsl(content))

                print ("\nPlease visit this Twitter page and retrieve the\n"
                    "pincode to be used in the next step to obtaining an\n"
                    "Authentication Token: %s?oauth_token=%s" %
                    (AUTHORIZATION_URL, request_token['oauth_token']))

                pincode = raw_input("Pincode? ")

                token = oauth2.Token(request_token["oauth_token"],
                    request_token["oauth_token_secret"])
                token.set_verifier(pincode)
                
                print "\nGenerating and signing request for an access token\n"

                oauth_client  = oauth2.Client(oauth_consumer, token)
                resp, content = oauth_client.request(ACCESS_TOKEN_URL,
                    method='POST', body="oauth_verifier=%s" % pincode)
                access_token  = dict(parse_qsl(content))

        if resp["status"] != "200":
                print ("The request for a Token did not succeed: "
                    "%s" % resp['status'])
                print access_token
        else:
                print ("Your Twitter Access Token key: %s" %
                    access_token['oauth_token'])
                print ("Access Token secret: %s" %
                    access_token['oauth_token_secret'])

        for key in ["oauth_token", "oauth_token_secret"]:
                if key not in access_token:
                        print "Unable to find %s in Twitter response." % key
                        sys.exit(1)
                config.set("feedplus", key, access_token[key])
        
        with open(config_path, 'wb') as configfile:
                config.write(configfile)
        os.chmod(config_path, 0600)

        return (access_token["oauth_token"], access_token["oauth_token_secret"])

def twitter_api(input_encoding="utf-8"):
        """Returns an API that we can use to talk to Twitter. """

        consumer_key = get_consumer_key()
        consumer_secret = get_consumer_secret()
        access_key, access_secret = \
                    get_access_tokens(consumer_key, consumer_secret)

        api = twitter.Api(consumer_key=consumer_key,
            consumer_secret=consumer_secret, access_token_key=access_key,
            access_token_secret=access_secret, input_encoding=input_encoding,
            debugHTTP=False)

        return api

def main():
        api = twitter_api()
        posts = api.GetUserTimeline("timfoster")
        for post in posts:
                print post

if __name__ == "__main__":
        main()



