"""
ComplexHTML XBlock for edX
Author: Raymond Lucian Blaga
Description: An HTML, JavaScript and CSS Editing XBlock that records student interactions if the course author wishes it.
"""

import urllib, datetime, json, smtplib, urllib2, sys, os, collections
import matplotlib.pyplot as plt
import numpy as np
from pylab import *
from pymongo import MongoClient
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEImage import MIMEImage
from .utils import render_template, load_resource
from django.template import Context, Template
from xblock.core import XBlock
from xblock.fields import Scope, Integer, List, String, Boolean, Dict
from xblock.fragment import Fragment

class ComplexHTMLXBlock(XBlock):

    mysql_database  = 'edxapp'
    mysql_user      = 'root'
    mysql_pwd       = ''

    display_name = String(
        display_name="ComplexHTML XBlock",
        help="This name appears in the horizontal navigation at the top of the page",
        scope=Scope.settings,
        default="ComplexHTML XBlock"
    )

    record_click = Boolean(
        help="Record student click?",
        default=True, scope=Scope.content
    )

    record_hover = Boolean(
        help="Record student hovers? (Note that this will flood the database; use with caution)",
        default=False, scope=Scope.content
    )

    tick_interval = Integer(
        default=60000,
        help="The time (in ms) between pings sent to the server (tied to sessions above)",
        scope=Scope.content
    )

    dev_stuff = Boolean(
        help="Show chx_dev_stuff div in LMS?",
        default=False, scope=Scope.content
    )

    dependencies = String(
        help="List of JS and CSS dependencies to be used in this XBlock",
        default="", scope=Scope.content
    )

    body_html = String(
        help="HTML code of the block",
        default="<p>Body of the block goes here...</p>", scope=Scope.content
    )

    body_tracked = String(
        help="List of tracked elements",
        default="p", scope=Scope.content
    )

    body_js_chunk_1 = String(
        help="JavaScript code for the block",
        default="console.log(\"Code before onload.\");", scope=Scope.content
    )

    body_js_chunk_2 = String(
        help="JavaScript code for the block, chunk #2",
        default="console.log(\"Onload event!\");", scope=Scope.content
    )

    body_json = String(
        help="JSON container that can be used by the JavaScript code above",
        default="{\"sample\": { \"subsample\": \"true\" }}",
        scope=Scope.content
    )

    body_json_timestamp = String(
        help="Timestamp from the last update made to body_json",
        default="",
        scope=Scope.content
    )

    body_css = String(
        help="CSS code for the block",
        default=".placeholderText { color: red }",
        scope=Scope.content
    )

    settings_student = String(
        help="Student-specific settings for student view in JSON form; initially a copy of body_json",
        default="",
        scope=Scope.user_state
    )

    settings_student_timestamp = String(
        help="Timestamp from the last update made to settings_student",
        default="",
        scope=Scope.user_state
    )

    grabbed = List(
        help="Student interaction that was grabbed from XBlock.",
        default=[], scope=Scope.user_state
    )

    sessions = List(
        default=[],
        help="List containing data on each session (ie, start time, end time)",
        scope=Scope.user_state
    )

    session_ended = Boolean(
        default=False,
        help="Has the student ended the current session yet?",
        scope=Scope.user_state
    )

    completed = Boolean(
        help="Completion status of this slide for the student.",
        default=False, scope=Scope.user_state
    )

    qz_attempted = Dict(
        help="Record how many attempts student have made",
        default={}, scope=Scope.user_state
    )
    n_user_id = String(
	display_name="UserId", default="0", scope=Scope.user_state, help="Id of the current user"
    )
    course_id = String(
    default="None", scope=Scope.user_state, help="Id of the current course"
    )
    conditional_id = Boolean(
        display_name = "Conditional", default = False, scope=Scope.user_state
    )
    totalWeight = Integer(
        default= 0, scope=Scope.user_state
    )
    has_score = True
    icon_class = 'other'

    @XBlock.json_handler
    def get_dependencies(self, data, suffix=''):
        return {"dependencies": self.dependencies}

    @XBlock.json_handler
    def get_body_html(self, data, suffix=''):
        return {"body_html": self.body_html}

    @XBlock.json_handler
    def get_body_css(self, data, suffix=''):
        return {"body_css": self.body_css}

    @XBlock.json_handler
    def get_body_js(self, data, suffix=''):
        return {"body_js": ("Chunk 1: \n" + self.body_js_chunk_1 + "\nChunk 2:\n" + self.body_js_chunk_2)}

    @XBlock.json_handler
    def get_body_json(self, data, suffix=''):
        return {"body_json": self.body_json}

    @XBlock.json_handler
    def get_settings_student(self, data, suffix=''):
        return {"json_settings": self.settings_student}

    @XBlock.json_handler
    def get_grabbed_data(self, data, suffix=''):
        return {"grabbed_data": self.grabbed}

    @XBlock.json_handler
    def get_completion_status(self, data, suffix=''):
        return {"completed": self.completed}

    def get_time_delta(self):
        """
        Return time difference between current grabbed input and the previous one.
        """
        return self.grabbed[-1] - self.grabbed[-2]

    @XBlock.json_handler
    def grab_data(self, data, suffix=''):
        """
        Grab data from recordable fields and append it to self.grabbed.
        """

        print ("CHX: Grabbed data from student: " + str(data))

        content = {"time": str(datetime.datetime.now())}
        chunk = []

        for i in data:
            chunk.append((str(i), str(data[i])))

        if len(chunk) > 0:
            self.grabbed.append((content["time"], chunk))
            content["data"] = chunk

        else:
            self.grabbed.append((content["time"], "crickets"))
            content["data"] = None

        print ("= ComplexHTML: Grabbed data on " + self.grabbed[-1][0])
        for i in self.grabbed[-1][1]:
            print ("= ComplexHTML: +--" + str(i))

        return content

    @XBlock.json_handler
    def get_user_data(self, data, suffix=''):
        """
        Get student data from the DB
        """
        import dbconnection

        # init default data
        user_id    = "None"
        user_name  = "None"
        user_email = "None"
        course_ids = "None"
        user_score = "0"
        # user and course
        db = dbconnection.mysql('localhost', 3306, self.mysql_database, self.mysql_user,self.mysql_pwd)
        q = "SELECT id, user_id, course_id FROM student_anonymoususerid WHERE anonymous_user_id='" + self.n_user_id + "'"
        db.query(q)
        res = db.fetchall()
        for row in res:
            user_id   = row[1]
            self.course_id = row[2]
        print user_id
        q = "SELECT course_id FROM student_courseenrollment WHERE user_id='%s' " % (user_id)
        db.query(q)
        res = db.fetchall()
        for row in res:
            course_ids = row[0]
        print course_ids
        labels = [course_ids, "System"]
        data =   [3.75               , 4.75]
        error =  [0.3497             , 0.3108]
        xlocations = np.array(range(len(data)))+0.5
        width = 0.5
        bar(xlocations, data, yerr=error, width=width)
        yticks(range(0, 8))
        xticks(xlocations+ width/2, labels)
        xlim(0, xlocations[-1]+width*2)
        title("Average Ratings on the Training Set")
        gca().get_xaxis().tick_bottom()
        gca().get_yaxis().tick_left()
        savefig('/tmp/test.png')
        # username
        q = "SELECT name FROM auth_userprofile WHERE user_id='%s' " % (user_id)
        db.query(q)
        res = db.fetchall()
        for row in res:
            #print row
            user_name = row[0]
        #print user_name
        # email
        q = "SELECT email FROM auth_user WHERE id='%s' " % (user_id)
        db.query(q)
        res = db.fetchall()
        for row in res:
            user_email   = row[0]
        strFrom = 'test@online.cdot.senecacollege.ca'
        strTo = 'to@example.com'
        msgRoot = MIMEMultipart('related')
        msgRoot['Subject'] = 'test message'
        msgRoot['From'] = strFrom
        msgRoot['To'] = strTo
        msgRoot.preamble = 'This is a multi-part message in MIME format.'
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)
        message = MIMEText('<b>Some <i>HTML</i> text</b> and an image.<br><img src="cid:image1"><br>Nifty!', 'html')
        msgAlternative.attach(message)
        msgRoot.attach(msgAlternative)
        fp = open('/tmp/test.png', 'rb')
       	msgImage = MIMEImage(fp.read())
      	fp.close()
        msgImage.add_header('Content-ID', '<image1>')
        msgRoot.attach(msgImage)
        try:
            #print ("INside")
            smtpObj = smtplib.SMTP('localhost', 25)
            smtpObj.ehlo()
            smtpObj.sendmail(strFrom, strTo, msgRoot.as_string())
            smtpObj.quit()
            #print ("Success")
        except:
            print ("Error")
        return {'user': user_email}

    def mongo_connection(self):
        """
        Connection to mongodb
        """
        client = MongoClient()
        db = client.edxapp
        return db

    def toSlidesColection(self):
        """
        Write to Slides collection
        """
        db = self.mongo_connection()
        chapter = self.get_chapter()
        sequential = self.get_sequential()
        vertical = self.get_vertical()
        dict_course = self.getDictCompleteCourseData(db.modulestore)
        snap_list = self.get_snaps(dict_course, chapter)
        slide_list = self.get_slides(dict_course, sequential)
        print("SLIDE")
        slide = db.slides.find()
        if (slide):
            print ("Hello")
        else:
            db.slides.insert({"_id" : slide_list["name"], "kc": {""}})
        module_structure = {"chapter" : chapter, "sequential" : sequential, "vertical" : vertical}

    def toStudentsCollection(self, data, correct_and_reason, slideid):
        """
        Write to Students collection
        """
        if data:
            check = 0
            attempt = 0
            quiz_dict = []
            print ("Student Collection")
            print correct_and_reason
            db = self.mongo_connection()
            slideid = self.get_vertical()
            student_exists = db.students.find_one({"_id": data["student_id"]})
            if (student_exists):
                student = db.students.find_one({"_id" : data["student_id"], "slides.slide_id" : slideid})
                if (student):
                    for slide in student.get("slides"):
                        for quiz in slide["quizzes"]:
                            quiz_dict.append(quiz["quiz_id"])
                            print ("Testing quizzes")
                            print quiz["quiz_id"]
                            print data['quizid']
                            print ("Quiz dict")
                            print quiz_dict
                            print check
                            if quiz["quiz_id"] == data['quizid']:
                                attempt = len(quiz["attempts"])
                                attempt += 1
                                print attempt
                                db.students.update({"_id": data["student_id"],"slides.slide_id": slideid, "slides.quizzes.quiz_id": data["quizid"]} , {"$push": {"slides.$.quizzes." + str(data['quizid']) + ".attempts":{"attempt": attempt, "kc": self.totalWeight, "answer_result": correct_and_reason["correct"]}}})
                            elif check == 0 and data['quizid'] not in quiz_dict:
                                db.students.update({"_id": data["student_id"], "slides.slide_id" : slideid} , {"$push": {"slides.$.quizzes": {"quiz_id" : data["quizid"], "attempts": [{ "attempt": 1, "kc": self.totalWeight, "answer_result":correct_and_reason["correct"]}], "type" : data["type"]}}})
                                check += 1
                else:
                    db.students.update({"_id": data["student_id"]} , {"$push": {"slides":{"slide_id" : slideid, "quizzes" :[{"quiz_id" : data["quizid"], "attempts": [{ "attempt": 1, "kc": self.totalWeight, "answer_result":     correct_and_reason["correct"]}], "type" : data["type"]}]}}})
            else:
                db.students.insert({"_id" : data["student_id"],"slides":[{"slide_id" : slideid, "quizzes" :[{"quiz_id" : data["quizid"], "attempts": [{ "attempt":data["attempts"], "kc": self.totalWeight, "answer_result":     correct_and_reason["correct"]}], "type" : data["type"]}]}]})
        return attempt

    def toQuizzesCollection(self, data):
        """
        Write to Quizzes collection
        """
        if data:
            db = self.mongo_connection()
            for dict in data:
                for slideId in dict:
                    print (dict.get(slideId).get("quizId"))

    def setParseCourseId(self):
        """
        Parse course_id name
        """
        if self.course_id !='' and self.course_id !='None':
            course  = self.course_id.split('/')
            corg= course[0]
            ccourse = course[1]
            cname = course[2]
            if corg!='' and ccourse!='' and cname!='':
                return course
            else:
                return ''

    def getDictCompleteCourseData(self,conn):
        """
        Get all data from mongo database
        for the given course as a dictionary
        """
        course = self.setParseCourseId()
        dict_course = []
        if course!='':
            corg = course[0]
            ccourse = course[1]
            cname = course[2]
            res_query = conn.find({'_id.org': ''+corg+'', '_id.course': ''+ccourse+'' }, {'definition.children':1, 'definition.data.bg_id':1, 'metadata.weight':1})
            if res_query:
                for item in res_query:
                    dict_course.append( self.getRecursiveData(item) )
        return dict_course

    def getRecursiveData(self,data):
        """
        Get data recursively
        """
        if isinstance(data, basestring):
            return str(data)
        elif isinstance(data, collections.Mapping):
            return dict(map(self.getRecursiveData, data.iteritems()))
        elif isinstance(data, collections.Iterable):
            return type(data)(map(self.getRecursiveData, data))
        else:
            return data

    def fetchPatternAndQuiz(self, data):
        """
        Fetch pattern id and quiz id from SlideId collection
        """
        db = self.mongo_connection()
        slides = db.slides.find()
        slideId = self.get_vertical()
        quizWeight = 0
        patternWeight = 0
        for key, value in enumerate(slides):
            if value["_id"] == slideId:
                quizList = value["quiz"]
                for quiz in quizList:
                    if int(quiz["id"]) == data["quizId"]:
                        quizWeight += int(quiz["weight"])
                patternList = value["pattern"]
                for pattern in patternList:
                    if pattern["id"] == data["patternId"] :
                        patternWeight += int(pattern["weight"])
        self.calculateTotalWeight(quizWeight, patternWeight )

    def fetchKcFromStudentsCollection(self, kcResultCursor):
        if (kcResultCursor):
            db = self.mongo_connection()
            result = []
            kc = 0
            slide = ""
            for key, studentValue in enumerate(kcResultCursor):
                for key, quizValue in enumerate(studentValue.get("slides")):
                    for key, slideValue in enumerate(db.modulestore.find({"_id.name" : quizValue.get("slide_id")})):
                        slide = slideValue.get("metadata")["display_name"]
                        for key, attemptsValue in enumerate(quizValue.get("quizzes")):
                            kc = attemptsValue.get("attempts")[-1]["kc"]
                        result.append({"slide_name": slide,"kc" : kc })
        return result

    def kcsToGraph(self, studentGraph):
        #Testing
        result = []
        studentData = {}

        db = self.mongo_connection()
        # modulestoreCollection = db.modulestore.find()
        #testin
        if (studentGraph["studentGraph"]):
            student_id = self.get_student_id()
            kcResultCursor = db.students.find({"_id" : student_id})
            kcSlideResult = self.fetchKcFromStudentsCollection(kcResultCursor)
            print "Test result"
            result.append(kcSlideResult)
            print result
        else:
            allStudents = db.students.find()
            for key, idValue in enumerate(allStudents):
                kcResultCursor = db.students.find({"_id": idValue.get('_id')})
                kcSlideResult = self.fetchKcFromStudentsCollection(kcResultCursor)
                print "Test result"
                result.append({"student_id": idValue.get("_id"), "slides" :kcSlideResult})
                print result
        return result

    def calculateTotalWeight(self, quizWeight, patternWeight, suffix=''):
        """
        Calculate total weight for knowledge component on slide
        """
        self.totalWeight = quizWeight + patternWeight
        print ("Total")
        print (quizWeight)
        print (patternWeight)
        if self.totalWeight >= 80:
            self.conditional_id = True

    @XBlock.json_handler
    def to_send(self, data, suffix=''):
        """
        Function that sends the condition of to proceed or not to next slide
        """
        return {"conditional_id" : self.conditional_id}

    @XBlock.json_handler
    def to_send_for_graph(self, data, suffix=''):
        """
        Function that sends kc and student_ids for graphs
        """
        return {"to_graph" : self.kcsToGraph(data)}

    @XBlock.json_handler
    def to_send_kc(self, data, suffix=''):
        """
        Function that sends the condition of to proceed or not to next slide
        """
        return {"kc" : self.totalWeight}

    def get_chapter(self):
        """
        Get current chapter from parent runtime
        """
        parent = self.get_parent()
        chapter = str(parent.get_parent().parent).split("/")[::-1][0]
        return chapter

    def get_sequential(self):
        """
        Get current sequential from parent runtime
        """
        parent = self.get_parent()
        sequential = str(parent.parent).split("/")[::-1][0]
        return sequential

    def get_vertical(self):
        """
        Get current vertical from parent runtime
        """
        parent = self.get_parent()
        vertical = str(self.parent).split("/")[::-1][0]
        return vertical

    def get_snaps(self,dict_course, sequential):
        """
        Get Snaps from current chapter
        """
        snap_list = []
        if len(dict_course) > 0:
            for key, value in enumerate(dict_course):
                if value.get("_id")["name"] == sequential and value.get("_id")["category"] == 'chapter':
                    children = value.get("definition")["children"]
                    if len(children) > 0:
                        for snap in children:
                            slides = self.get_slides(dict_course,snap.split('/')[::-1][0])
                            snap_list.append({"category" : "snap", "module_id" : snap, "name" : snap.split("/")[::-1][0], "slides": slides})
        return snap_list

    def get_slides(self, dict_course, chapter):
        """
        Get Slides from current chapter
        """
        slide_list = []
        if len(dict_course) > 0:
            for key, value in enumerate(dict_course):
                if value.get('_id')['name']==chapter and value.get('_id')['category']=='sequential':
                    children = value.get('definition')['children']
                    if len(children) > 0:
                        for k in children:
                            slide_list.append( {'category': 'slide', 'module_id' : k, 'name' : k.split('/')[::-1][0]})
        return slide_list

    @XBlock.json_handler
    def clear_data(self, data, suffix=''):
        """
        Clear data grabbed from student
        """
        del self.grabbed[:]
        return {"cleared": "yes"}

    @XBlock.json_handler
    def update_student_settings(self, data, suffix=''):
        """
        Update student settings from AJAX request
        """
        if self.settings_student != data["json_settings"]:
            self.settings_student = json.dumps(data["json_settings"])
            return {"updated": "true"}

        return {"updated": "false"}

    @XBlock.json_handler
    def session_start(self, data, suffix=''):
        """
        Start a new student session and record the time when it happens
        """

        self.session_ended = False
        print ("= ComplexHTML: Session started at: " + str(datetime.datetime.now()))
        self.sessions.append([str(datetime.datetime.now()), "", ""])

        return {}

    @XBlock.json_handler
    def session_tick(self, data, suffix=''):
        """
        Record a periodic tick while the student views this XBlock.
        A safety measure in case their browser or tab crashes.
        """

        if len(self.sessions) > 0:

            if not self.session_ended:

                print ("= ComplexHTML: Session tick at: " + str(datetime.datetime.now()))
                self.sessions[-1][1] = str(datetime.datetime.now())

        return {}

    @XBlock.json_handler
    def session_end(self, data, suffix=''):
        """
        End a student session and record the time when it happens
        """

        if len(self.sessions) > 0:

            if not self.session_ended:

                print ("= ComplexHTML: Session ended at: " + str(datetime.datetime.now()))
                self.sessions[-1][2] = str(datetime.datetime.now())
                self.session_ended = True

        return {}

    @staticmethod
    def get_num_sessions(self):
        print ("Self sessions")
        print self.sessions
        return len(self.sessions)

    @XBlock.json_handler
    def complete_block(self, data, suffix=''):
        """
        Mark this XBlock as completed for the student
        """
        self.completed = True
        return {}

    @staticmethod
    def url_loader(strin, sep):
        """
        Load contents of all URLs from strin, separated by sep and return a compiled string
        """
        strout = ""

        for line in strin.split(sep):
            if line[:4] == "http":
                strout += urllib.urlopen(line).read().decode('utf-8')
            # else ignore line

        return strout

    @staticmethod
    def generate_html(html):

        result = "<div class=\"complexhtml_xblock\">"
        # Assume valid HTML code
        result += html
        result += "</div>"

        return result

    @staticmethod
    def generate_js(self, jsa, jsb, tracked="", record=[]):

        # Load first chunk of the JS script
        # result = load_resource('static/js/complexhtml_lms_chunk_1.js')
        result = render_template('static/js/complexhtml_lms_chunk_1.js', {'self': self})

        # Generate AJAX request for each element that will be tracked
        tracked_str = ""

        for i in tracked.split("\n"):

            if "click" in record:
                e = i.split(", ")
                tracked_str += "recordClick(\'" + e[0] + "\'"
                if len(e) > 1:
                    tracked_str += ", \'" + e[1] + "\'"
                tracked_str += ");\n"

            if "hover" in record:
                e = i.split(", ")
                tracked_str += "recordHover(\'" + e[0] + "\'"
                if len(e) > 1:
                    tracked_str += ", \'" + e[1] + "\'"
                tracked_str += ");\n"

        # Adding tracking calls
        result += "/* Elements being recorded go here */\n" + tracked_str

        # Add first staff entered chunk - ie the code running before the onLoad
        result += "\n\n/* Staff entered JS code */\n"
        result += "try {\n"
        result += "eval(\"" + jsa.replace("\"", "\\\"").replace("\'", "\\\'").replace("\n", "\\n\" + \n\"") + "\"\n);"
        result += "\n\n} catch (err) {\n"
        result += "    console.log(\"ComplexHTML caught this error in pre-run JavaScript code: \" + err);\n"
        result += "    $(\'.chx_javascript_error\').show();\n"
        result += "    $(\'.complexhtml_xblock\').hide();\n"
        result += "}\n"

        # Add second JavaScript chunk
        # result += "\n" + load_resource('static/js/complexhtml_lms_chunk_2.js')
        result += "\n" + render_template('static/js/complexhtml_lms_chunk_2.js', {'self': self})

        # Add second staff entered chunk - ie the code running on page load
        result += "\n/* Staff entered JS code */\n"
        result += "try {\n"
        result += "eval(\"" + jsb.replace("\"", "\\\"").replace("\'", "\\\'").replace("\n", "\\n\" + \n\"") + "\"\n);"
        result += "\n\n} catch (err) {\n"
        result += "    console.log(\"ComplexHTML caught this error in pre-run JavaScript code: \" + err);\n"
        result += "    $(\'.chx_javascript_error\').show();\n"
        result += "    $(\'.complexhtml_xblock\').hide();\n"
        result += "}\n"
        result += "\n})\n\n}"

        return result

    @staticmethod
    def generate_css(css, preview=False):

        result = ""
        tmp = css

        if preview:
            block_name = ".complexhtml_preview"
        else:
            block_name = ".complexhtml_xblock"

        # Prefix all CSS entries with XBlock div name to ensure they apply
        for i in tmp.split('\n'):
            if i.find('{') != -1:
                result += block_name + " " + i
            else:
                result += i
            result += '\n'

        return result

    @XBlock.json_handler
    def get_generated_css(self, data, suffix=''):
        """
        Generate CSS text fo block and return it via AJAX request
        """
        content = {"css": ""}
        if self.body_css != "" and data["block"] != "":
            content["css"] = self.generate_css(self.body_css, true)
            return content
        return content

    @staticmethod
    def generate_dependencies(dependencies):
        """
        Generate HTML tags for JS and CSS dependencies
        """

        css_pile = ""
        js_pile = ""

        # load JS and CSS dependencies
        for line in dependencies.split('\n'):

            if line[:4] == "http":

                if line[-4:] == ".css":
                    css_pile += "<link rel=\"stylesheet\" href=\"" + line + "\" />\n"

                if line[-3:] == ".js":
                    js_pile += "<script src=\"" + line + "\"></script>\n"

                # else ignore; not a valid asset

            # else ignore; not a valid link

        return css_pile + js_pile

    @XBlock.json_handler
    def get_generated_dependencies(self, data, suffix=''):
        """
        Generate HTML tags for JS and CSS dependencies and return them via AJAX request
        """
        content = {"dependencies": ""}
        if self.dependencies != "":
            content["dependencies"] = self.generate_dependencies(self.dependencies)
            return content
        return content

    @staticmethod
    def update_student_settings_backend(source, settings):
        """
        Returns dictionary that is source merged with settings
        """
        result = json.loads(source)
        result.update(json.loads(settings))
        return json.dumps(result)

    @XBlock.json_handler
    def get_clean_body_json(self, data, suffix=''):
        body_json = json.loads(self.settings_student)
        return {"body_json_clean": body_json}

    def get_student_id(self):
        """
         Get data from student_id
        """
        if hasattr(self, "xmodule_runtime"):
            s_id = self.xmodule_runtime.anonymous_student_id
        else:
            if self.scope_ids.user_id == None:
                s_id = "None"
            else:
                s_id = unicode(self.scope_ids.user_id)
        return s_id

    @XBlock.json_handler
    def get_quiz_attempts(self, data, suffix =''):

        correct_and_reason = {}
        attempt_for_conditionals = 0
        quiz_attempts = {}
        attempt = 1
        body_json = json.loads(self.body_json)
        quizId = 0
        patternId = 0
        slide_id = 0
        actionId = False
        student_id = self.get_student_id()
        print("Student_id")
        print(student_id)
        if data['ch_question']:
            print ("Ch_question")
            print (data['ch_question'])
            for key, value in data['ch_question'].iteritems():
                if key == "selectedQuizId":
                   quizId = int(value)
                if key == "patternId":
                    patternId = value
                if key == "actionId":
                    actionId = value
                if key == "slide_id":
                    slide_id = value
            print("Quiz value")
            quiz_type = data["ch_question"]["quiz_id"].split("_")
            quiz_attempts.update({'student_id' : student_id, 'quizid' : quizId, 'attempts' : attempt, "type": quiz_type[0]})
            self.qz_attempted = data['ch_question'].copy()
        for item in xrange(len(body_json["quizzes"])):

            if item == int(self.qz_attempted["selectedQuizId"]):
                if int(self.qz_attempted['correct']) == int(self.qz_attempted['selected']):
                    correct_and_reason.update({'correct': 'true'})
                else:
                    correct_and_reason.update({'correct': 'false'})
        result = {"quizId": quizId, "patternId": patternId, "actionId": actionId}
        attempt_for_conditionals = self.toStudentsCollection(quiz_attempts, correct_and_reason, slide_id)
        self.fetchPatternAndQuiz(result)
        print("End of attempts")
        return {"quiz_result_id": correct_and_reason, "attempts": attempt_for_conditionals}

    def student_view(self, context=None):
        """
        The student view
        """

        fragment = Fragment()
        content = {'self': self}
        self.n_user_id = self.get_student_id()

        # copy over body_json to settings_student if the latter is blank
        if self.settings_student == "":
            self.settings_student_timestamp = self.body_json_timestamp
            self.settings_student = self.body_json

        # settings_student isn't blank
        else:

            # compare timestamps
            if self.settings_student_timestamp != self.body_json_timestamp:

                # settings_student is outdated in this case, it must be updated
                self.settings_student = self.update_student_settings_backend(self.settings_student, self.body_json)
                self.settings_student_timestamp = self.body_json_timestamp

            # else all is in order, keep going

        body_html = self.generate_dependencies(self.dependencies) + unicode(self.generate_html(self.body_html))

        fragment.add_css(unicode(self.generate_css(self.body_css)))
        fragment.add_css(load_resource('static/css/complexhtml.css'))

        fragment.add_content(Template(body_html).render(Context(content)))
        fragment.add_content(render_template('templates/complexhtml.html', content))

        record = []

        if self.record_click:
            record.append("click")
        if self.record_hover:
            record.append("hover")

        fragment.add_javascript(unicode(
            self.generate_js(
                self,
                self.body_js_chunk_1,
                self.body_js_chunk_2,
                self.body_tracked,
                record
            )
        ))
        fragment.initialize_js('ComplexHTMLXBlock')

        return fragment

    def studio_view(self, context=None):
        """
        The studio view
        """

        fragment = Fragment()
        content = json.loads(load_resource("static/studio_settings.json"))
        content['self'] = self

        try:
            urllib2.urlopen(content["CKEDITOR_URL"])
        except urllib2.HTTPError, e:
            content["CKEDITOR_URL"] = ""
        except urllib2.URLError, e:
            content["CKEDITOR_URL"] = ""

        if self.tick_interval < 1000:
            self.tick_interval = 86400000  # 24 hrs

        # Load CodeMirror
        fragment.add_javascript(load_resource('static/js/codemirror/lib/codemirror.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/mode/xml/xml.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/mode/htmlmixed/htmlmixed.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/mode/javascript/javascript.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/mode/css/css.js'))
        fragment.add_css(load_resource('static/js/codemirror/lib/codemirror.css'))

        # Load CodeMirror add-ons
        fragment.add_css(load_resource('static/js/codemirror/theme/mdn-like.css'))
        fragment.add_javascript(load_resource('static/js/codemirror/addon/edit/matchbrackets.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/addon/edit/closebrackets.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/addon/search/search.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/addon/search/searchcursor.js'))
        fragment.add_javascript(load_resource('static/js/codemirror/addon/dialog/dialog.js'))
        fragment.add_css(load_resource('static/js/codemirror/addon/dialog/dialog.css'))

        # Load Studio View
        fragment.add_content(render_template('templates/complexhtml_edit.html', content))
        fragment.add_css(load_resource('static/css/complexhtml_edit.css'))
        fragment.add_javascript(unicode(render_template('static/js/complexhtml_edit.js', content)))
        fragment.initialize_js('ComplexHTMLXBlockStudio')

        return fragment

    @staticmethod
    def generate_preview(self, dependencies, html, json, jsa, jsb, css):

        preview = ""

        # disabled for now due to time constraints

        #preview += self.generate_dependencies(dependencies)

        # style tag

        #preview += self.generate_css(css, True)

        # style tag

        # script tag

        # json_settings = { contents of json from arguments }

        # jsa

        # function preview_run() {
        #   jsb
        # };

        # script tag

        # ".complexhtml_preview" div

        #preview += self.generate_html(html)

        # ".complexhtml_preview" div

        return preview

    @XBlock.json_handler
    def studio_submit(self, data, suffix=''):
        """
        Course author pressed the Save button in Studio
        """

        result = {"submitted": "false", "saved": "false", "message": "", "preview": ""}

        if len(data) > 0:

            # Used for the preview feature
            # if data["commit"] == "true":

            # NOTE: No validation going on here; be careful with your code
            self.display_name = data["display_name"]
            self.vertical_name = data["display_name"]
            self.record_click = data["record_click"] == 1
            self.record_hover = data["record_hover"] == 1
            self.tick_interval = int(data["tick_interval"])
            self.dev_stuff = data["dev_stuff"] == 1
            self.dependencies = data["dependencies"]
            self.body_html = data["body_html"]
            self.body_tracked = data["body_tracked"]
            self.body_json = data["body_json"]
            self.body_json_timestamp = str(datetime.datetime.now())
            self.body_js_chunk_1 = data["body_js_chunk_1"]
            self.body_js_chunk_2 = data["body_js_chunk_2"]
            self.body_css = data["body_css"]

            if self.tick_interval < 1000:
                self.tick_interval = 86400000  # 24 hrs

            result["submitted"] = "true"
            result["saved"] = "true"

            ''' # Used for previewing feature
            elif data["commit"] == "false":

                result["submitted"] = "true"
                result["preview"] = self.generate_preview(
                    self,
                    data["dependencies"],
                    data["body_html"],
                    data["body_json"],
                    data["body_js_chunk_1"],
                    data["body_js_chunk_2"],
                    data["body_css"]
                )

            else:
                print ("Invalid commit flag. Not doing anything.")

            '''

        return result

    @staticmethod
    def workbench_scenarios():
        """A canned scenario for display in the workbench."""
        return [
            ("complexhtml",
             """<vertical_demo>
                <complexhtml/>
                </vertical_demo>
             """),
        ]
