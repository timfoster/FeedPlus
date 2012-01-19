#!/usr/bin/python2.6
# coding=utf-8

# Copyright (c) 2011 Tim Foster
# 
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the
# "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
# 
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY
# CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
# TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


# A very basic python script to produce an Atom feed from
# a given G+ ID.

import ConfigParser
import cgi
import codecs
import os
import uuid
import sys

import apiclient.discovery
import httplib2
import os.path

import settings
import fp_twitter

from lxml import etree

# Not using this yet
#
#from oauth2client.client import OAuth2WebServerFlow
#from oauth2client.tools import run
#from oauth2client.file import Storage
from StringIO import StringIO

class PlusEntry(object):
        """Capture the content of a single G+ post.
        Really need a __repr__ or __str__ method, sorry.
        """

        def __init__(self, activity=None):
                """
                Create a new PlusEntry object, wrapping the G+ activity in a
                more straightforward object.  Needs work to capture more of
                the activity content I care about.

                """
                self.author = activity['actor']['displayName']
                self.author_id = activity['actor']['id']

                self.post = activity['object']['content']
                self.annotation = activity.get('annotation', None)

                # when resharing, the author and the post_author can be
                # different
                self.post_author = None
                self.post_id = None
                if 'actor' in activity['object']:
                        self.post_author = activity['object']['actor']['displayName']
                        self.post_id = activity['object']['actor']['id']
                
                self.datestamp = activity['updated']      
                self.permalink = activity['url']
                self.links = []
                if 'attachments' in activity['object']:
                        attach = activity['object']['attachments'][0]
                        if 'image' in attach:
                                self.links.append(attach['image']['url'])
                        else:
                                self.links.append(attach['url'])


def build_service(credentials, http, api_key=None):
        """For now, credentials are always None"""
        if ( credentials != None ):
            http = credentials.authorize(http)
        service = apiclient.discovery.build('plus', 'v1', http=http,
            developerKey=api_key)

        return service

def pull_from_plus(plus_id="107847990164269071741"):
        """Given a Google Plus id, return a list of activity json objects.
        """

        # Lifted from Google's Python example cli - for now, we're
        # only doing public feed content.
        #
        # http = httplib2.Http()
        # credentials = authorize_self(settings.CLIENT_ID,settings.CLIENT_SECRET)
        # service = build_service(credentials,http)

        # person = service.people().get(userId='me').execute(http)
        # print "Got your ID: " + person['displayName']

        httpUnauth = httplib2.Http()
        serviceUnauth = build_service(None, httpUnauth, settings.API_KEY)

        activities = []
        npt = ""

        while (npt != None):
                activities_doc = serviceUnauth.activities().list(
                    userId=plus_id,collection="public").execute(httpUnauth)

                if "items" in activities_doc:
                        activities += activities_doc["items"]

                if not 'nextPageToken' in activities_doc or \
                    activities_doc["nextPageToken"] == npt:
                        "---Done"
                break

                npt = activities_doc["nextPageToken"]
        return activities

def atom_header(entry):
        """return a basic atom header, based on
        a single PlusEntry object."""
        author = entry.author
        uuidstr = uuid.uuid5(uuid.NAMESPACE_DNS, author)
        date = entry.datestamp
        return """<?xml version="1.0" encoding="utf-8"?>
 
 <feed xmlns="http://www.w3.org/2005/Atom">
  
          <title>G+ Atom Feed for %(author)s</title>
                  <id>urn:uuid:%(uuidstr)s</id>
                  <updated>%(date)s</updated>
                  <author>
                        <name>%(author)s</name>
                  </author>
""" % locals()

def atom_footer():
        """No templating here, just returning a
        text string.  We may want to expand this later."""
        return "</feed>\n"

def render_atom_entry(entry):
        """Our default entry format."""
        post = truncate_post(entry)
        post_dic = {"title": "G+ post: %s ..." % cgi.escape(trunc(post, 50)),
            "link": entry.permalink,
            "date": entry.datestamp,
            "uuid": uuid.uuid5(uuid.NAMESPACE_URL,
                entry.author + entry.datestamp),
            "summary": cgi.escape(post),
            "permalink": entry.permalink }

        return """
        <entry>
                <title>%(title)s</title>
                <link href="%(permalink)s" />
                <id>urn:uuid:%(uuid)s</id>
                <updated>%(date)s</updated>
                <summary>%(summary)s</summary>
        </entry>
""" % post_dic

def html_to_plaintext(text):
        """try to get readable plaintext from the G+ html.   Lxml doesn't
        seem to do <br> elements properly."""
        text = text.replace("<br />", " ")
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(text), parser)
        return etree.tounicode(tree.getroot(), method="text")

def trunc(str, max_size=140):
        """Basic sring truncation"""
        if len(str) > max_size:
                return str[0:max_size - 3] + "..."
        return str 

def truncate_post(entry):
        """Want to shorten the entry to 140 chars.  Any longer than that
        and we simply provide a link to the original.
        """
        annotation = None

        # if we have comments on a shared post, use those in preference
        # to the post itself
        if entry.annotation:
                annotation = cgi.escape(html_to_plaintext(entry.annotation))

        post = ""
        if entry.post:
                post = cgi.escape(html_to_plaintext(entry.post))

        if entry.post_id and not entry.annotation:
                post = "RT +%s: %s" % (entry.post_author, post)
        elif entry.post_id and entry.annotation:
                post = "%s QT +%s: %s " % (annotation, entry.post_author, post)

        if entry.links:
                url = entry.links[0].strip()
                if post:
                        post = "%s %s" % (post, url)
                else:
                        post = url

        if len(post) > 140:
                post = "%s %s" % (trunc(post, max_size=75), entry.permalink)

        return post
                        
def render_atom_feed(plus_entries):
        if not plus_entries:
                print "No G+ Entries found!"
                sys.exit(1)

        atom_entries = []
        atom_entries.append(atom_header(plus_entries[0]))

        for entry in plus_entries:
                atom_entries.append(render_atom_entry(entry))
        atom_entries.append(atom_footer())
        return "\n".join(atom_entries)

def update_twitter(entries):
        """Write a list of entries to Twitter, using the "last_post" key in
        ~/.feedplusrc and only posting items newer than that."""
        
        api = fp_twitter.twitter_api()
        config_path = os.path.expanduser("~/.feedplusrc")
        config = ConfigParser.ConfigParser()
        config.read([config_path])
        last_post = config.get("feedplus", "last_post")
        if not last_post:
                # totally arbitrary value
                last_post = "2011-12-12T01:21:15.790Z"

        # look for new posts, posting in chronological order
        posted = False
        for entry in reversed(entries):
                text = truncate_post(entry)
                if entry.datestamp > last_post:
                        posted = True
                        # api.PostUpdate(text)
                        print "posting %s" % entry.datestamp

        if posted:
                config.set("feedplus", "last_post", entries[0].datestamp)
                with open(config_path, 'wb') as configfile:
                        config.write(configfile)
                        os.chmod(config_path, 0600)

def main():

        if len(sys.argv) < 4:
                print "Usage: feedplus.py <G+ id> <dir> True|False (write to Twitter)"
                sys.exit(2)

        activities = pull_from_plus(plus_id=sys.argv[1])

        entries = []
        for activity in activities:
                entries.append(PlusEntry(activity))
        atom = open("%s/atom.xml" % sys.argv[2], "w")
        atom.write(codecs.encode(render_atom_feed(entries), "utf-8"))
        atom.close()

        if sys.argv[3].lower() == "true":
                update_twitter(entries)

if __name__ == "__main__":
        main()
