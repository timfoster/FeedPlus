#!/usr/bin/python

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

import cgi
import os
import re
import simplejson
import urllib2
import uuid
import sys

from collections import namedtuple
from datetime import datetime

# Links are straightforward - a namedtuple will suffice
PlusLink = namedtuple("LinkEntry",
    ["title", "img_url", "desc", "link_url", "link_type", "thumb"])


class PlusEntry(object):
        """Capture the content of a single G+ post.
        Really need a __repr__ or __str__ method, sorry.
        """

        def __init__(self, json_obj=None):
                """
                Create a new PlusEntry object.  If json_obj is
                supplied, we populate it with content from that
                object, according to the following:

                [3] = Author
                [16] = Author id
                [4] = Full HTML text
                [5] = Unix timestamp followed by 3 digits for ms
                [7] = Comments
                [11] = Array of one or more links
                [11][x][3] = Title of link
                [11][x][5][1] = URL of image uploaded
                [11][x][21] = Description of link
                [11][x][24][1] = Linked URL
                [11][x][24][4] = Type: document, image, photo, video
                [11][x][41][0][1] = Thumbnail of image
		[20] = Plaintext of post
                [21] = Link to Google+ page for the post
                """
                self.author = None
                self.author_id = None
                self.post = None
                self.datestamp = None
                self.comments = []
                self.links = []
                self.permalink = None
                if not json_obj:
                        return
                self.author = json_obj[3]
                self.author_id = json_obj[16]
                self.post = json_obj[4]
                self.datestamp = datetime.fromtimestamp(float(json_obj[5])/1000)

                self.comments = [PlusComment(c) for c in json_obj[7]]
                self.plaintext = json_obj[20]
                self.permalink = "https://plus.google.com/%s" % json_obj[21]

                # Gather as much as we can about each link
                for i in range(0, len(json_obj[11])):
                        title = None
                        img_url = None
                        desc = None
                        link_url = None
                        link_type = None
                        thumb = None

                        # this is pretty horrid
                        try:
                                title = json_obj[11][i][3]
                        except:
                                pass
                        try:
                                img_url = json_obj[11][i][5][1]
                        except:
                                pass
                        try:   
                                desc = json_obj[11][i][21]
                        except:
                                pass
                        try:
                                link_url = json_obj[11][i][24][1]
                        except:
                                pass
                        try:
                                link_type = json_obj[11][i][24][4]
                        except:
                                pass
                        try:
                                thumb = json_obj[11][i][41][0][1]
                        except:
                                pass

                        link = PlusLink(title, img_url, desc, link_url, link_type, thumb)
                        self.links.append(link)

class PlusComment(PlusEntry):
        """A comment to a PlusEntry - could probably be expanded."""
        def __init__(self, json_obj=None):
                """Create a new PlusComment object. If json_obj is
                provided, we populate the PlusEntry with contents from
                that object.
                """
                self.post = None
                self.author = None
                self.author_id = None
                self.datestamp = None
                if not json_obj:
                        return
                self.post = json_obj[2]
                self.author = json_obj[1]
                self.author_id = json_obj[6]
                self.datestamp = datetime.fromtimestamp(float(json_obj[3])/1000)

def pull_from_plus(plus_id="107847990164269071741"):
        """Given a Google Plus id, return a text string
        containing the JSON returned.
        """

        commas = re.compile(",,",re.M)

        head = \
            "https://plus.google.com/_/stream/getactivities/%(plusid)s/?sp=" % \
            {"plusid": plus_id}    
        tail = \
            '[1    ,2,"%(plusid)s",null,null,null,null,"social.google.com",[]]' % \
            {"plusid": plus_id}
        url = head + urllib2.quote(tail)
        try:
                response = urllib2.urlopen(url)
        except urllib2.URLError, err:
                raise ValueError("failed to open url: %s" % err)

        if not response or response.code != 200:
                raise ValueError("HTTP %s" % response.code)

        # formatting with newlines makes life easier when
        # reading the text file from a terminal when debugging
        txt = "\n".join([line.rstrip() for line in response.readlines()])

        # the Google plus response contains JSON with missing
        # nulls and a leading string, ")]}'\n".  Remove that
        # string, and replace the nulls.
        txt = txt[5:]
        txt = commas.sub(",null,",txt)
        txt = commas.sub(",null,",txt)
        txt = txt.replace("[,","[null,")
        txt = txt.replace(",]",",null]")

        # cache the json to a flat file, useful when debugging
        if os.environ.get("FEEDPLUS_DEBUG"):
                f = open("./json", "w")
                f.write(txt)
                f.close()
        return txt

def atom_header(entry):
        """return a basic atom header, based on
        a single PlusEntry object."""
        author = entry.author
        uuidstr = uuid.uuid5(uuid.NAMESPACE_DNS, author)
        date = entry.datestamp.strftime("%Y-%m-%dT%H:%M:%SZ")
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
        text = "         <entry>\n"
        post = truncate_post(entry)

        post_dic = {"title": "G+ post: %s ..." % cgi.escape(trunc(post, 50)),
            "link": entry.permalink,
            "date": entry.datestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "uuid": uuid.uuid5(uuid.NAMESPACE_DNS, post.encode(
                "ascii", "ignore")),
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

def trunc(str, max_size=140):
        """Basic sring truncation"""
        if len(str) > max_size:
                return str[0:max_size - 3] + "..."
        return str 

def truncate_post(entry):
        """Want to shorten the entry to 140 chars if
        possible, but if it includes a link or photo,
        try to ensure that gets added to the post at
        the expense of the text.
        """
        # zorch html
        post = entry.plaintext

        # only ever include 1 link
        if entry.links:
                url = ""
                if entry.links[0].link_url:
                        url = entry.links[0].link_url.strip()
                elif entry.links[0].img_url:
                        url = entry.links[0].img_url.strip()
                url = url.rstrip("/")
                if url not in post:
                        # simple case
                        if len(post) + len(url) + 1 <= 140:
                                return "%s %s" % (post, url)
                        url_len = len(url)
                        # add dots to show abbreviated content
                        # we should do more to shorten links (bit.ly?)
                        if url_len <= 140:
                                size = 140 - url_len - 2
                                return "%s %s" % (trunc(post, size), url)
        return trunc(post)
                        
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


def main():

        if len(sys.argv) < 3:
                print "Usage: feedplus.py <G+ id> <dir>"
                sys.exit(2)

        # some code to help debugging/testing
        if not os.path.exists("./json"):
                json = pull_from_plus(plus_id=sys.argv[1])
        else:
                f = open("./json", "r")
                json = f.read()
                f.close()

        obj = simplejson.loads(json)
        # having an array with just the json entries for
        # the public feed is useful when debugging
        json_entries = obj[1][0]
        entries = []
        for entry in json_entries:
                entries.append(PlusEntry(entry))
        atom = open("%s/atom.xml" % sys.argv[2], "w")
        atom.write(render_atom_feed(entries).encode("UTF-8"))
        atom.close()

if __name__ == "__main__":
        main()
