from flask import Flask, abort, request, jsonify, g, url_for, send_from_directory
from os import sep
from youtube_transcript_api import YouTubeTranscriptApi
import time
import random
import string
import math
import json
from rdflib import Graph, Literal

from datetime import datetime
from flask_httpauth import HTTPBasicAuth
import jwt
import pymongo
import bcrypt
from flask_mongoengine import MongoEngine
from flask_mail import Mail, Message
from smtplib import SMTPException, SMTPRecipientsRefused
import urllib.request
import json
import urllib
import urllib.parse

import data
import handle_data
from environment import APP_SECRET_KEY, MONGO_CLUSTER_USERNAME, MONGO_CLUSTER_PASSWORD, EMAIL_ACCOUNT, EMAIL_PASSWORD


app = Flask(__name__)
app.config['SECRET_KEY'] = APP_SECRET_KEY

#segment images directory
app.config["CLIENT_IMAGES"] = "/var/www/ekeel/EVA_apps/EKEELVideoAnnotation/static/videos"


#mongo db config
app.config['MONGODB_SETTINGS'] = {
    'db': 'ekeel',
    'host': "mongodb+srv://"+MONGO_CLUSTER_USERNAME+":"+MONGO_CLUSTER_PASSWORD+"@clusteredurell.z8aeh.mongodb.net/edurell?retryWrites=true&w=majority"
}



#mail server config (gmail account date of birth : 01/01/1900)
#old: <project.edurell@gmail.com> <work$package>
app.config['MAIL_SERVER']='smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = EMAIL_ACCOUNT
app.config['MAIL_PASSWORD'] = EMAIL_PASSWORD
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_DEFAULT_SENDER'] = 'edurellannotator@gmail.com'

#recovery of email project.edurell thomas.neveux@etu.utc.fr

# extensions
auth = HTTPBasicAuth(scheme='Custom')
db = MongoEngine()
db.init_app(app)
mail = Mail(app)



# generate a random string of lenght N composed of lowercase letters and numbers
def generate_code(N=6):
    """
    Generates a random string of length N composed of lowercase letters and numbers.

    Parameters
    ----------
    N : int, optional
        The length of the generated string (default is 6).

    Returns
    -------
    str
        The generated random string.
    """
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(N))


# Get the speech from a youtube video URL
@app.route('/api/youtube_transcript', methods=["GET", "POST"])
def speech_from_youtube():
    """
    Retrieves the speech transcript from a YouTube video URL.

    Parameters
    ----------
    None

    Returns
    -------
    flask.Response
        A JSON response containing the speech transcript and video metadata.
    """
    req = request.get_json(force=True)
    videoId=req.get('video_id')

    collection = pymongo.MongoClient(
        "mongodb+srv://"+MONGO_CLUSTER_USERNAME+":"+MONGO_CLUSTER_PASSWORD+"@clusteredurell.z8aeh.mongodb.net/edurell?retryWrites=true&w=majority").ekeel.videos
    
    video_metadata = collection.find_one({"video_id": videoId})
    languages = []
    if video_metadata is not None and "language" in video_metadata.keys():
        languages.append(video_metadata["language"])
    languages.append("en")
    transcript = YouTubeTranscriptApi.get_transcript(videoId, languages=languages)
    subs_dict = []
    for sub in transcript:
        start = get_integer_part(sub["start"])
        duration = get_integer_part(sub["duration"])
        subs_dict.append(
            {
                "text": sub["text"],
                "start": start,
                "end": start + duration
            }
        )
    result = jsonify(subs_dict)
    return result


# get the integer part of a number
# ex: for 2.5 it will return 2
def get_integer_part(number):
    """
    Get the integer part of a number.

    Parameters
    ----------
    number : float
        Input number

    Returns
    -------
    float
        Integer part of the number
    """
    split_number = math.modf(number)
    return split_number[1]
    
class VTStitles(db.EmbeddedDocument):
    """
    Embedded document for video text segmentation titles.

    Attributes
    ----------
    start_end_seconds : list
        List of start and end times in seconds
    text : str
        Text content of the title
    xywh_normalized : list
        List of normalized bounding box coordinates
    """
    start_end_seconds = db.ListField(db.DecimalField())
    text = db.StringField()
    xywh_normalized = db.ListField(db.DecimalField())
    
class VideoTextSegmentation(db.Document):
    """
    Document for video text segmentation data.

    Attributes
    ----------
    video_id : str
        Identifier for the video
    slides_percentage : float
        Percentage of slides in the video
    slide_titles : list
        List of VTStitles embedded documents
    slide_startends : list
        List of start and end times for slides
    slidish_frames_startend : list
        List of start and end frames for slides
    """
    video_id = db.StringField()
    slides_percentage = db.DecimalField()
    slide_titles = db.EmbeddedDocumentListField(VTStitles)
    slide_startends = db.ListField(db.ListField(db.DecimalField()))
    slidish_frames_startend = db.ListField(db.ListField(db.IntField()))

#image of the mongodb collection of the database, used by mongoengine
class Videos(db.Document):
    """
    Document for video metadata.

    Attributes
    ----------
    video_id : str
        Identifier for the video
    title : str
        Title of the video
    creator : str
        Creator of the video
    duration : str
        Duration of the video
    segment_starts : list
        List of segment start times
    segment_ends : list
        List of segment end times
    extracted_keywords : list
        List of extracted keywords
    language : str
        Language of the video
    """
    video_id = db.StringField()
    title = db.StringField()
    creator = db.StringField()
    duration = db.StringField()
    segment_starts = db.ListField(db.StringField())
    segment_ends = db.ListField(db.StringField())
    extracted_keywords = db.ListField(db.StringField())
    language = db.StringField()

#image of the mongodb collection of the database, used by mongoengine
class VideoStatistics(db.Document):
    """
    Document for video statistics.

    Attributes
    ----------
    video_url : str
        URL of the video
    amountViewers : int
        Number of viewers
    total_fragment_clicks : int
        Total number of fragment clicks
    total_node_clicks : int
        Total number of node clicks
    total_transcript_clicks : int
        Total number of transcript clicks
    total_searchbar_clicks : int
        Total number of search bar clicks
    viewersList : list
        List of viewer emails
    """
    video_url = db.StringField()
    amountViewers = db.IntField()
    total_fragment_clicks = db.IntField()
    total_node_clicks = db.IntField()
    total_transcript_clicks = db.IntField()
    total_searchbar_clicks = db.IntField()
    viewersList = db.ListField(db.StringField())

#image of the mongodb collection of the database, used by mongoengine
class HistoryLog(db.EmbeddedDocument):
    """
    Embedded document for history logs.

    Attributes
    ----------
    date : datetime
        Date of the log entry
    request : str
        Request content
    """
    date = db.DateTimeField()
    request = db.StringField()

#image of the mongodb collection of the database, used by mongoengine
class Fragment(db.EmbeddedDocument):
    """
    Embedded document for video fragments.

    Attributes
    ----------
    name : str
        Name of the fragment
    start : str
        Start time of the fragment
    end : str
        End time of the fragment
    progress : int
        Progress of the fragment
    """
    name = db.StringField()
    start = db.StringField()
    end =  db.StringField()
    progress = db.IntField()

#image of the mongodb collection of the database, used by mongoengine
class VideoHistory(db.EmbeddedDocument):
    """
    Embedded document for video history.

    Attributes
    ----------
    video_url : str
        URL of the video
    video_watchtime : int
        Watch time of the video
    fragment_clicks : int
        Number of fragment clicks
    node_clicks : int
        Number of node clicks
    transcript_clicks : int
        Number of transcript clicks
    searchbar_clicks : int
        Number of search bar clicks
    notes : str
        Notes for the video
    lastChangesDate : datetime
        Date of the last changes
    fragments_progress : list
        List of Fragment embedded documents
    logs : list
        List of HistoryLog embedded documents
    """
    video_url = db.StringField()
    video_watchtime = db.IntField()
    fragment_clicks = db.IntField()
    node_clicks = db.IntField()
    transcript_clicks = db.IntField()
    searchbar_clicks = db.IntField()
    notes = db.StringField()
    lastChangesDate = db.DateTimeField()
    fragments_progress = db.EmbeddedDocumentListField(Fragment)
    logs = db.EmbeddedDocumentListField(HistoryLog)


# image of the mongodb collection of the database, used by mongoengine
# also have some methods related to the fields of the class
class Student(db.Document):
    """
    Document for student data.

    Attributes
    ----------
    name : str
        First name of the student
    surname : str
        Last name of the student
    email : str
        Email address of the student
    password_hash : str
        Hashed password of the student
    code_reset_password : str
        Code for resetting password
    nb_try_code_reset_password : int
        Number of attempts for resetting password
    code_delete_account : str
        Code for deleting account
    nb_try_code_delete_account : int
        Number of attempts for deleting account
    video_history_list : list
        List of VideoHistory embedded documents

    Methods
    -------
    hash_password(password)
        Hash the student's password
    verify_password(password)
        Verify the student's password
    hash_code_reset_password(code)
        Hash the code for resetting password
    verify_code_reset_password(code)
        Verify the code for resetting password
    hash_code_delete_account(code)
        Hash the code for deleting account
    verify_code_delete_account(code)
        Verify the code for deleting account
    generate_auth_token(expires_in)
        Generate an authentication token
    verify_auth_token(token)
        Verify an authentication token
    get_sorted_history(by)
        Get sorted video history
    """
    name = db.StringField()
    surname = db.StringField()
    email = db.StringField()
    password_hash = db.StringField()

    code_reset_password = db.StringField()
    nb_try_code_reset_password = db.IntField()

    code_delete_account = db.StringField()
    nb_try_code_delete_account = db.IntField()

    video_history_list:list = db.EmbeddedDocumentListField(VideoHistory)

    def hash_password(self, password):
        hashed_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.password_hash = hashed_pwd.decode('utf8')
        self.save()

    def verify_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))



    def hash_code_reset_password(self, code):
        hashed_code = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt())
        self.code_reset_password = hashed_code.decode('utf8')
        self.save()

    def verify_code_reset_password(self, code):
        nb_try_code_reset_password_to_increment = self.nb_try_code_reset_password
        if nb_try_code_reset_password_to_increment is None:
            nb_try_code_reset_password_to_increment=0
        self.nb_try_code_reset_password = nb_try_code_reset_password_to_increment+ 1
        self.save()
        return bcrypt.checkpw(code.encode('utf-8'), self.code_reset_password.encode('utf-8'))



    def hash_code_delete_account(self, code):
        hashed_code = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt())
        self.code_delete_account = hashed_code.decode('utf8')
        self.save()

    def verify_code_delete_account(self, code):
        nb_try_code_delete_account_to_increment = self.nb_try_code_delete_account
        if nb_try_code_delete_account_to_increment is None:
            nb_try_code_delete_account_to_increment=0
        self.nb_try_code_delete_account = nb_try_code_delete_account_to_increment + 1
        self.save()
        return bcrypt.checkpw(code.encode('utf-8'), self.code_delete_account.encode('utf-8'))



    def generate_auth_token(self, expires_in=600):
        #return jwt.encode(
        #    {'email': self.email, 'exp': time.time() + expires_in},
        #    app.config['SECRET_KEY'], algorithm='HS256')
        return jwt.encode(
            {'email': self.email},
            app.config['SECRET_KEY'], algorithm='HS256')


    @staticmethod
    def verify_auth_token(token):
        try:
            data = jwt.decode(token, app.config['SECRET_KEY'],
                              algorithms=['HS256'])
        except:
            return
        return Student.objects(email=data['email']).first()
    

    def get_sorted_history(self,by:str):
        docs = self.video_history_list.copy()

        if by == "title":
            comp_funct = lambda video: get_video_title_from_url(video.video_url.split("watch?v=")[1])
        elif by == "lastChange":
            comp_funct = lambda video: video.lastChangesDate

        n = len(docs)
        # optimize code, so if the array is already sorted, it doesn't need
        # to go through the entire process
        # Traverse through all array elements
        for i in range(n):
        
            # range(n) also work but outer loop will
            # repeat one time more than needed.
            # Last i elements are already in place
            swapped = False
            for j in range(0, n-i-1):
            
                # traverse the array from 0 to n-i-1
                # Swap if the element found is greater
                # than the next element
                if comp_funct(docs[j]) > comp_funct(docs[j + 1]):
                    swapped = True
                    docs[j], docs[j + 1] = docs[j + 1], docs[j]

            if not swapped:
                # if we haven't needed to make a single swap, we
                # can just exit the main loop.
                return docs[::-1] if by == "lastChange" else docs
            


#image of the mongodb collection of the database, used by mongoengine
# this is used to store the accounts that are not verified yet with the confirmation code sent by mail
class UnverifiedStudent(db.Document):
    """
    Document for unverified student data.

    Attributes
    ----------
    name : str
        First name of the student
    surname : str
        Last name of the student
    email : str
        Email address of the student
    password_hash : str
        Hashed password of the student
    code_on_creation_hash : str
        Code for account creation
    nb_try_code_on_creation : int
        Number of attempts for account creation

    Methods
    -------
    hash_password(password)
        Hash the student's password
    hash_code_on_creation(code)
        Hash the code for account creation
    verify_code_on_creation(code)
        Verify the code for account creation
    """
    name = db.StringField()
    surname = db.StringField()
    email = db.StringField()
    password_hash = db.StringField()

    code_on_creation_hash = db.StringField()
    nb_try_code_on_creation = db.IntField()


    def hash_password(self, password):
        hashed_pwd = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        self.password_hash = hashed_pwd.decode('utf8')
        self.save()

    def hash_code_on_creation(self, code):
        hashed_code = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt())
        self.code_on_creation_hash = hashed_code.decode('utf8')
        self.save()

    def verify_code_on_creation(self, code):
        nb_try_code_on_creation_to_increment = self.nb_try_code_on_creation
        if nb_try_code_on_creation_to_increment is None:
            nb_try_code_on_creation_to_increment=0
        self.nb_try_code_on_creation = nb_try_code_on_creation_to_increment+ 1
        self.save()
        return bcrypt.checkpw(code.encode('utf-8'), self.code_on_creation_hash.encode('utf-8'))

#function used by the authentication system. If it returns true, the user is considered as logged in, false he's not
@auth.verify_password
def verify_password(email_or_token, password):
    """
    Verify user password or token for authentication.

    Parameters
    ----------
    email_or_token : str
        Email or authentication token
    password : str
        User password

    Returns
    -------
    bool
        True if authentication is successful, False otherwise
    """
    # first try to authenticate by token
    student = Student.verify_auth_token(email_or_token)
    if not student:
        # try to authenticate with email/password
        student = Student.objects(email=email_or_token).first()
        if not student or not student.verify_password(password):
            return False
    g.student = student
    return True

# api to call to create a new account
@app.route('/api/register', methods=['POST'])
def new_student():
    """
    Register a new student account.

    Returns
    -------
    flask.Response
        JSON response with the student's email
    """
    email_input = request.json.get('email')
    password_input = request.json.get('password')
    name_input = request.json.get('name')
    surname_input = request.json.get('surname')
    if email_input is None or password_input is None or name_input is None or surname_input is None:
        abort(400)    # missing arguments
    if Student.objects(email=email_input).first() is not None:
        abort(409, "An account have already been created with this mail")    # existing student
    existingUnverifiedStudent = UnverifiedStudent.objects(email=email_input).first()
    if existingUnverifiedStudent is not None:
        existingUnverifiedStudent.delete()

    generated_code_creation = generate_code()
    # create an UnverifiedStudent and save it in the db
    unverifiedStudent = UnverifiedStudent(email=email_input, name= name_input, surname = surname_input,nb_try_code_on_creation = 0)
    unverifiedStudent.hash_password(password_input)
    unverifiedStudent.hash_code_on_creation(generated_code_creation)
    unverifiedStudent.save()

    #send a mail with the verification code
    msg = Message('EKEEL- Code to finalize your account creation', recipients = [email_input])
    msg.body = "Hello, welcome to EKEEL ! \n Your validation code to finalize your account creation : "+ generated_code_creation
    try:
        mail.send(msg)
    except SMTPRecipientsRefused:
        abort(406,"invalid mail")
    except :
        abort(503, "error returned by the email sending service")
    return (jsonify({'email': unverifiedStudent.email}), 201)

# api to call to finalize your account creation (verify that your code is correct)
@app.route('/api/register/verify', methods=['POST'])
def verify_mail():
    """
    Verify email and code for account creation.

    Returns
    -------
    flask.Response
        JSON response with the student's email
    """
    email_input = request.json.get('email')
    code_input = request.json.get('code')
    if email_input is None or code_input is None:
        abort(400, "The code or the email is missing")    # missing arguments
    if Student.objects(email=email_input).first() is not None:
        abort(409,"An account have already been created with this mail")    # existing student
    unverifiedStudent = UnverifiedStudent.objects(email=email_input).first()
    if unverifiedStudent is None:
        abort(404, "No temporary student found, please restart register from the beginning")    # not existing UnverifiedStudent
    if not unverifiedStudent.verify_code_on_creation(code_input):
        if unverifiedStudent.nb_try_code_on_creation is not None and unverifiedStudent.nb_try_code_on_creation>5:
            unverifiedStudent.delete()
            abort(403, "Too many wrong validation code, please restart register from the beginning")
        abort(401, "Wrong validation code")

    #after the checks have passed, create a Student in the db and delete the UnverifiedStudent from the db
    student = Student(email = unverifiedStudent.email, name = unverifiedStudent.name, surname = unverifiedStudent.surname, password_hash = unverifiedStudent.password_hash)
    student.save()
    unverifiedStudent.delete()
    return (jsonify({'email': student.email}), 201)


# api to call to retrieve your password, it will send you a code by mail that you will need to return with your new password to the next api to finalize the operation
@app.route('/api/retrieve_password', methods=['POST'])
def send_code_to_reset_password_by_mail():
    """
    Send code to reset password via email.

    Returns
    -------
    flask.Response
        JSON response with the student's email
    """
    email_input = request.json.get('email')
    if email_input is None:
        abort(400)    # missing arguments
    student = Student.objects(email=email_input).first()
    if student is None:
        abort(409, "No account associated with this mail")    # no existing student
    generated_code_reset_password = generate_code()
    student.hash_code_reset_password(generated_code_reset_password)
    student.save()

    #send a mail with the verification code
    msg = Message('EKEEL- Code to change your password', recipients = [email_input])
    msg.body = "Hello ! \n Here is your validation code to change your password : "+ generated_code_reset_password
    mail.send(msg)
    return (jsonify({'email': student.email}), 201)

# api to call to reset your password, you need to have the right code to validate the operation
@app.route('/api/retrieve_password/verify', methods=['POST'])
def verify_code_and_change_password():
    """
    Verify code and change password.

    Returns
    -------
    flask.Response
        JSON response with the student's email
    """
    email_input = request.json.get('email')
    code_input = request.json.get('code')
    new_password_input = request.json.get('password')
    if email_input is None or code_input is None:
        abort(400, "The code or the email is missing")    # missing arguments
    student = Student.objects(email=email_input).first()
    if student is None:
        abort(409, "No account exists with this mail")    # no existing student
    if not student.verify_code_reset_password(code_input):
        if student.nb_try_code_reset_password is not None and student.nb_try_code_reset_password>5:
            student.code_reset_password = None
            student.nb_try_code_reset_password = None
            student.save()
            abort(403, "Too many wrong validation codes, please restart the password retrieval procedure")
        abort(401, "Wrong validation code")

    else:
        student.hash_password(new_password_input)
        student.code_reset_password = None
        student.nb_try_code_reset_password = None
        student.save()
        return (jsonify({'email': student.email}), 201)


# api to call to change your name and surname, no code required
@app.route('/api/change_name_and_surname', methods=['POST'])
@auth.login_required
#the above line require that the credentials (mail/password or token) are sent in the request to login th user
def change_name_and_surname():
    """
    Change student's name and surname.

    Returns
    -------
    flask.Response
        JSON response with the student's email, new name, and new surname
    """
    name_input = request.json.get('name')
    surname_input = request.json.get('surname')
    if name_input is None or surname_input is None:
        abort(400, "The new name or/and the new surname is/are missing")    # missing arguments
    student= g.student
    student.name = name_input
    student.surname = surname_input
    student.save()
    return (jsonify({'email': student.email, 'newName': name_input, 'newSurname': surname_input}), 201)


# api to call to delete your account, it will send you a code by mail that you will need to return to the next api to finalize the operation
@app.route('/api/delete_account', methods=['POST'])
@auth.login_required
def send_code_to_delete_account_by_mail():
    """
    Send code to delete account via email.

    Returns
    -------
    flask.Response
        JSON response with the student's email
    """
    email_input = request.json.get('email')
    if email_input is None:
        abort(400)    # missing arguments
    student = Student.objects(email=email_input).first()
    if student is None:
        abort(409, "No account associated with this mail")    # no existing student
    generated_code_delete_account = generate_code()
    student.hash_code_delete_account(generated_code_delete_account)
    student.save()

    #send a mail with the verification code
    msg = Message('EKEEL- Code to delete your account', recipients = [email_input])
    msg.body = "Hello ! \n Here is your validation code to delete your account : "+ generated_code_delete_account+"\n Be carefull, account deletion can't be undone"
    mail.send(msg)
    return (jsonify({'email': student.email}), 201)

# api to call to delete your account, you need to have the right code to validate the operation
@app.route('/api/delete_account/verify', methods=['POST'])
@auth.login_required
def verify_code_and_delete_account():
    """
    Verify code and delete account.

    Returns
    -------
    flask.Response
        JSON response with the student's email
    """
    email_input = request.json.get('email')
    code_input = request.json.get('code')
    if email_input is None or code_input is None:
        abort(400, "The code or the email is missing")    # missing arguments
    student = Student.objects(email=email_input).first()
    if student is None:
        abort(409, "No account exists with this mail")    # no existing student
    if not student.verify_code_delete_account(code_input):
        if student.nb_try_code_delete_account is not None and student.nb_try_code_delete_account>5:
            student.code_delete_account = None
            student.nb_try_code_delete_account = None
            student.save()
            abort(403, "Too many wrong validation codes, please restart the account deletion procedure")
        abort(415, "Wrong validation code")

    else:
        data.delete_graphs(email_input)
        student.delete()
        return (jsonify({'email': student.email}), 201)


# return the name and surname of the student
@app.route('/api/get_user_infos')
@auth.login_required
def get_student():
    """
    Get student's name, surname, and email.

    Returns
    -------
    flask.Response
        JSON response with the student's name, surname, and email
    """
    return jsonify({'name': g.student.name, 'surname':g.student.surname, 'email': g.student.email})

#return an authentication token, valid for a certain amount of time
@app.route('/api/token')
@auth.login_required
def get_auth_token():
    """
    Get authentication token.

    Returns
    -------
    flask.Response
        JSON response with the token, duration, name, and surname
    """
    token = g.student.generate_auth_token()
    return jsonify({'token': token, 'duration': None, 'name': g.student.name, 'surname':g.student.surname})


#update the user history for one specific video
@app.route('/api/update_user_history',  methods=['POST'])
@auth.login_required
def add_history():
    """
    Update user history for a specific video.

    Returns
    -------
    flask.Response
        JSON response with the student's email
    """
    student= g.student
    #get data from request
    video_url_input = request.json.get('url')
    video_watchtime_input = request.json.get('video_watchtime')
    fragment_clicks_input = request.json.get('fragment_clicks')
    node_clicks_input = request.json.get('node_clicks')
    transcript_clicks_input = request.json.get('transcript_clicks')
    searchbar_clicks_input = request.json.get('searchbar_clicks')
    notes_input = request.json.get('notes')
    fragments_input = request.json.get('fragments')

    if video_url_input is None:
        abort(400, "The video url is missing")    # missing arguments

    #set None numbers to zero to avoid errors in the sums
    if fragment_clicks_input is None:
        fragment_clicks_input=0
    if node_clicks_input is None:
        node_clicks_input=0
    if transcript_clicks_input is None:
        transcript_clicks_input=0
    if searchbar_clicks_input is None:
        searchbar_clicks_input=0


    videoHistory=None
    try :
        #case where the student already watched the video and the history exsists for this video
        videoHistory = student.video_history_list.get(video_url=video_url_input)

        if video_watchtime_input is not None:
            videoHistory.video_watchtime= video_watchtime_input

        if notes_input is not None:
            videoHistory.notes= notes_input

        if fragments_input is not None:
            if videoHistory.fragments_progress is not None:
                videoHistory.fragments_progress.delete()
            for item in fragments_input:
                new_fragment = Fragment(name = item['name'], start= item['start'], end= item['end'], progress=item['progress'])
                videoHistory.fragments_progress.append(new_fragment)


        videoHistory.fragment_clicks = videoHistory.fragment_clicks + fragment_clicks_input
        videoHistory.node_clicks = videoHistory.node_clicks + node_clicks_input
        videoHistory.transcript_clicks = videoHistory.transcript_clicks + transcript_clicks_input
        videoHistory.searchbar_clicks = videoHistory.searchbar_clicks + searchbar_clicks_input
        videoHistory.lastChangesDate = datetime.now()

        new_log = HistoryLog(date = datetime.now(), request = str(request.json) )
        videoHistory.logs.append(new_log)

    except:

        #case where the student have not already watched the video, we need to create a VideoHistory object for this video

        if video_watchtime_input is None:
            video_watchtime_input=0

        if notes_input is None:
            notes_input=''



        videoHistory = VideoHistory(video_url = video_url_input, video_watchtime = video_watchtime_input, fragment_clicks = fragment_clicks_input, node_clicks = node_clicks_input, transcript_clicks = transcript_clicks_input,  searchbar_clicks = searchbar_clicks_input, notes = notes_input, lastChangesDate = datetime.now())

        new_log = HistoryLog(date = datetime.now(), request = str(request.json) )
        videoHistory.logs.append(new_log)

        if fragments_input is not None:
            for item in fragments_input:
                new_fragment = Fragment(name = item['name'], start= item['start'], end= item['end'], progress=item['progress'])
                videoHistory.fragments_progress.append(new_fragment)

        student.video_history_list.append(videoHistory)

    student.save()

    #store global video statistics
    videoStatistics = VideoStatistics.objects(video_url = video_url_input).first()

    if videoStatistics is None :
        videoStatistics = VideoStatistics(video_url = video_url_input, total_fragment_clicks = fragment_clicks_input, total_node_clicks = node_clicks_input, total_transcript_clicks = transcript_clicks_input,  total_searchbar_clicks = searchbar_clicks_input, amountViewers = 1)
        videoStatistics.viewersList.append(student.email)

    else:
        videoStatistics.total_fragment_clicks = videoStatistics.total_fragment_clicks + fragment_clicks_input
        videoStatistics.total_node_clicks = videoStatistics.total_node_clicks + node_clicks_input
        videoStatistics.total_transcript_clicks = videoStatistics.total_transcript_clicks + transcript_clicks_input
        videoStatistics.total_searchbar_clicks = videoStatistics.total_searchbar_clicks + searchbar_clicks_input

        if videoStatistics.viewersList.count(student.email)==0 :
            videoStatistics.viewersList.append(student.email)
            videoStatistics.amountViewers = videoStatistics.amountViewers + 1


    videoStatistics.save()
    return (jsonify({'email': student.email}), 201)

# return the history of a user
@app.route('/api/get_user_history')
@auth.login_required
def get_history():
    """
    Get user's video history.

    Returns
    -------
    flask.Response
        JSON response with the student's email, video history, and video titles
    """
    student:Student = g.student
    video_title_list = []
    
    # Removing videos that have been removed from videos collection
    for video_in_history in reversed(student.video_history_list):
        if not Videos.objects(video_id = video_in_history.video_url.split("watch?v=")[1]):
            student.video_history_list.remove(video_in_history)

    history_list = student.get_sorted_history(by="lastChange")

    for video in history_list:
        video_title_list.append(get_video_title_from_url(video.video_url.split("watch?v=")[1]))
        #print(video," ",get_video_title_from_url(video.video_url.split("watch?v=")[1]))
    
    return (jsonify({'email': student.email, 'videoHistory' : history_list, 'videoHistoryTitles': video_title_list}), 201)

# used in the function above to get youtube video title based on their id
def get_video_title_from_url(video_id):
    """
    Get YouTube video title based on video ID.

    Parameters
    ----------
    video_id : str
        YouTube video ID

    Returns
    -------
    str
        Video title
    """
    #print("GET VIDEO: ",video_id)
    params = {"format": "json", "url": "https://www.youtube.com/watch?v=%s" % video_id}
    url = "https://www.youtube.com/oembed"
    query_string = urllib.parse.urlencode(params)
    url = url + "?" + query_string
    #print("url ",url)

    #print("dopo")

    with urllib.request.urlopen(url) as response:
        response_text = response.read()
        data = json.loads(response_text.decode())
    return data['title']

    


# return the fragment of a video and their progress, can be taken from the Video mongodb collection or from the user's history if he already watched it
@app.route('/api/get_fragments/<string:video_id>')
@auth.login_required
def get_fragments(video_id):
    """
    Get video fragments and their progress.

    Parameters
    ----------
    video_id : str
        Identifier for the video

    Returns
    -------
    flask.Response
        JSON response with the student's email, fragments, and keywords
    """
    student= g.student
    video_url = "https://www.youtube.com/watch?v=%s" % video_id
    video_fragment_progress = None
    for i in student.video_history_list:
        if video_url == i.video_url:
            '''print(i.fragments_progress)
            for e in i.fragments_progress:
                print(e.name)'''

            video_fragment_progress = i.fragments_progress
    graph_object = Graphs.objects(video_id = video_id, email = student.email).first()

    #if user first time on this video open first available video
    if(graph_object is None):
        graph_object = Graphs.objects(video_id = video_id).first()

    #if then graph still not exist show msg
    if graph_object is None:
        abort(409, "Unexisting graph for this video id")    # the video doesn't exist in the graphs collection

    keywords = handle_data.get_definitions_fragments(graph_object.email, video_id, video_fragment_progress)

    if(video_fragment_progress is None or not len(video_fragment_progress)):
        
        video = Videos.objects(video_id = video_id).first()
        
        #if then video not exist show msg
        if video is None:
            abort(409, "video not in the catalog")    # the video is not in the catalog

        segment_amount = len(video.segment_starts)
        video_fragment_progress = []
        
        '''if video_id =="sXLhYStO0m8":
            names = ["Sex determination Pelvis Sciatic notch", "Pre-auricular sulcus Ventral arc Iliopubic ramus","Skull","Eye sockets", "Forehead Mastoid process Posterior zygomatich arch", "Nuchal crest", "Femur"]
            for i in range(segment_amount):
                video_fragment_progress.append({'name': names[i], 'start' : time.strftime('%H:%M:%S', time.gmtime(int(round(video.segment_starts[i])))),  'end' : time.strftime('%H:%M:%S', time.gmtime(int(round(video.segment_ends[i])))), 'progress':0 })

        else:'''

        for i in range(segment_amount):
            video_fragment_progress.append({'name': 'Part %s'%(i+1), 'start' : time.strftime('%H:%M:%S', time.gmtime(int(round(video.segment_starts[i])))),  'end' : time.strftime('%H:%M:%S', time.gmtime(int(round(video.segment_ends[i])))), 'progress':0 })

        

    return (jsonify({'email': student.email, 'fragments' : video_fragment_progress, 'keywords':keywords}), 201)

# return the list of every video available on the db
@app.route('/api/get_catalog')
@auth.login_required
def get_catalog():
    """
    Get list of all available videos in the database.

    Returns
    -------
    flask.Response
        JSON response with the video catalog
    """
    graphs = Graphs.objects()
    videos = Videos.objects()

    catalog = []
    
    for v in videos:
        for gr in graphs:
            if v.video_id == gr.video_id:
                if v not in catalog:
                    catalog.append(v)


    return (jsonify({'catalog': catalog}), 201)


#image of the mongodb collection of the database, used by mongoengine
class Graphs(db.Document):
    """
    Document for graph data.

    Attributes
    ----------
    video_id : str
        Identifier for the video
    annotator_name : str
        Name of the annotator
    annotator_id : str
        Identifier for the annotator
    email : str
        Email of the annotator
    graph : dict
        Graph data
    conceptVocabulary : dict
        Concept vocabulary data
    """
    video_id = db.StringField()
    annotator_name = db.StringField()
    annotator_id = db.StringField()
    email = db.StringField()
    graph = db.DynamicField()
    conceptVocabulary = db.DynamicField()


#get the complete json graph from a video (put the video_id in the route)
@app.route('/api/get_graph/<string:video_id>')
@auth.login_required
def get_graph(video_id=None):
    """
    Get complete JSON graph for a video.

    Parameters
    ----------
    video_id : str, optional
        Identifier for the video

    Returns
    -------
    flask.Response
        JSON response with the student's email, graph, and concept vocabulary
    """
    if video_id is None:
        abort(400, "The video id is missing")    # missing arguments
    student= g.student
    graph_object = Graphs.objects(video_id = video_id, email=student.email).first()

    #if user first time on this video open first available video
    if(graph_object is None):
        graph_object = Graphs.objects(video_id = video_id).first()

    #if then graph still not exist show msg
    if graph_object is None:
        abort(409, "Unexisting graph for this video id")    # the video doesn't exist in the graphs collection

    if graph_object.conceptVocabulary is None:
        graph_object.conceptVocabulary = False

    return (jsonify({'email': student.email, 'graph' : graph_object.graph, 'conceptVocabulary': graph_object.conceptVocabulary}), 201)


# return the image of a fragment, the image is stored on the local files of the server
@app.route("/api/get_image/<string:video_id>/<int:fragment_index>")
def get_image(video_id=None, fragment_index=None ):
    """
    Get image of a video fragment.

    Parameters
    ----------
    video_id : str, optional
        Identifier for the video
    fragment_index : int, optional
        Index of the fragment

    Returns
    -------
    flask.Response
        Image file response
    """
    if video_id is None or fragment_index is None:
        abort(400, "The video id or the image name is missing")    # missing arguments

    #get the starting time of the segment to know the image file name
    video = Videos.objects(video_id = video_id).first()
    if video is None:
        abort(409, "video not in the catalog")    # the video doesn't exist

    #segment_starting_time = None
    #try :
    #    segment_starting_time = video.segment_starts[fragment_index]
    #except IndexError:
    #    abort(409, "fragment index out of range ")

    #image_name = str(segment_starting_time).replace('.','_')+'.jpg'
    image_name = str(fragment_index).replace('.','_')+'.jpg'
    try:
        return send_from_directory(app.config["CLIENT_IMAGES"]+sep+video_id, image_name, as_attachment=True)
    except FileNotFoundError:
        abort

#return the graph user ids of a given video
@app.route('/api/graph_id/<video_id>')
@auth.login_required
def graph_id(video_id):
    """
    Get graph user IDs for a given video.

    Parameters
    ----------
    video_id : str
        Identifier for the video

    Returns
    -------
    dict
        Dictionary containing list of graph IDs
    """
    print("***** EKEEL - Video Augmentation: main.py::graph_id(): Inizio ******")
    student= g.student
    graph_list = handle_data.check_graphs(video_id,student.email)

    # if user first time on this video, select all available graph ids
    if not len(graph_list):
        graph_list = handle_data.get_graphs(video_id)
    print(graph_list)
    print("***** EKEEL - Video Augmentation: main.py::graph_id(): Fine ******")

    return {"graphs_id_list": graph_list }


#return the graph of a given video
@app.route('/api/graph/<annotator_id>/<video_id>')
@auth.login_required
def graph(annotator_id, video_id):
    """
    Get graph for a given video and annotator.

    Parameters
    ----------
    annotator_id : str
        Identifier for the annotator
    video_id : str
        Identifier for the video

    Returns
    -------
    dict
        Dictionary containing concepts list and concept vocabulary
    """
    concept_graph = data.build_array(annotator_id, video_id)

    # old: return {"conceptsList": concept_graph }
    
    conceptVocabulary = data.get_concept_vocabulary(annotator_id, video_id)

    # If the concept vocabulary is new (empty) in DB then initialize it to empty synonyms
    if(conceptVocabulary == None) :
        conceptVocabulary = {}
        concept_list = data.get_concept_list(annotator_id, video_id)
        for c in concept_list:
            conceptVocabulary[c["name"][4:].replace("_", " ")] = []    

    return {"conceptsList": concept_graph, "conceptVocabulary": conceptVocabulary}

@app.route('/api/GetVideoTypeAndPrerequisite')
@auth.login_required
def GetVideoTypeAndPrerequisite():
    """
    Get video type and prerequisite information.

    Returns
    -------
    dict
        Dictionary containing video type and prerequisite information
    """
    client = pymongo.MongoClient(
        "mongodb+srv://"+MONGO_CLUSTER_USERNAME+":"+MONGO_CLUSTER_PASSWORD+"@clusteredurell.z8aeh.mongodb.net/edurell?retryWrites=true&w=majority")

    # retrieve from mongodb collection=graphs the all elements with the value of video_id
    db = client.ekeel
    collection = db.graphs

    videos = Videos.objects()
    result={}
    for v in videos:
        cursor = collection.find({"video_id":v.video_id})


        
        for document in cursor:
            #print("per ogni document in cursor: ",document["_id"]," ",document["conceptVocabulary"])
            #print("\n asd \n")
            if document["conceptVocabulary"] == "":
                print("NONE")
                continue

            gr=Graph()
            print("Generato grafo: ")
            # Query the concept timeline and duration
            gr.parse(data=json.dumps(document["graph"]), format='json-ld')

            # initialize conceptVocabulary for the query
            gr.parse(data=json.dumps(document["conceptVocabulary"]), format='json-ld')
           
        
        qr="""
                PREFIX oa: <http://www.w3.org/ns/oa#>
                PREFIX edu: <https://teldh.github.io/edurell#>
                PREFIX dctypes: <http://purl.org/dc/dcmitype/>
                PREFIX dcterms: <http://purl.org/dc/terms/>
                PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

                SELECT DISTINCT ?video_id ?prerequisite ?typedef
                WHERE{
                    ?id_descr oa:motivatedBy oa:describing.
                    ?id_descr oa:hasTarget ?target_descr.
                    ?target_descr oa:hasSource ?video_id.
                    ?id_descr skos:note  ?typedef.

                    ?id_pre oa:motivatedBy edu:linkingPrerequisite.
                    ?id_pre oa:hasTarget ?target_link.
                    ?target_link oa:hasSource ?video_id.
                    ?id_pre oa:hasBody ?prerequisiteIRI.
                    ?prerequisiteIRI skos:prefLabel ?prerequisite.
                    

                }
        
        """
        print("applico la query")
        qres = gr.query(qr)
        print("qres: ",len(qres)," ",qr)
        for row in qres:
            #print("_________________________________________")
            #print(row['video_id']," ",row['prerequisite']," ",row['typedef'])
            if v.video_id in result:
                if "prerequisite" in result[v.video_id]:
                    result[v.video_id]["prerequisite"].append(row['prerequisite'])
                else:
                    result[v.video_id]["prerequisite"] = []
                    result[v.video_id]["prerequisite"].append(row['prerequisite'])
                
                if "typedef" in result[v.video_id]:
                    result[v.video_id]["typedef"].append(row['typedef'])
                else:
                    result[v.video_id]["typedef"] = []
                    result[v.video_id]["typedef"].append(row['typedef'])
            else:
                result[v.video_id] = {}
                if "prerequisite" in result[v.video_id]:
                    result[v.video_id]["prerequisite"].append(row['prerequisite'])
                else:
                    result[v.video_id]["prerequisite"] = []
                    result[v.video_id]["prerequisite"].append(row['prerequisite'])
                
                if "typedef" in result[v.video_id]:
                    result[v.video_id]["typedef"].append(row['typedef'])
                else:
                    result[v.video_id]["typedef"] = []
                    result[v.video_id]["typedef"].append(row['typedef'])
    
        VTS=VideoTextSegmentation.objects(video_id = v.video_id)
        for VTSdoc in VTS:
            print(VTSdoc.video_id)
            print(VTSdoc.slides_percentage)
            if v.video_id in result:
                result[v.video_id]['slides_percentage'] = VTSdoc.slides_percentage
            else:
                result[v.video_id] = {}
                result[v.video_id]['slides_percentage'] = VTSdoc.slides_percentage
    return result

@app.route('/api/ConceptVideoData/<video_id_list>/<concept_searched>')
@auth.login_required
def ConceptVideoData(video_id_list, concept_searched):
    """
    Get concept video data for a list of videos.

    Parameters
    ----------
    video_id_list : str
        Comma-separated list of video IDs
    concept_searched : str
        Concept to search for

    Returns
    -------
    str
        JSON string containing concept video data
    """
    #pymongo db config for query sparql
    client = pymongo.MongoClient(
            "mongodb+srv://"+MONGO_CLUSTER_USERNAME+":"+MONGO_CLUSTER_PASSWORD+"@clusteredurell.z8aeh.mongodb.net/edurell?retryWrites=true&w=majority")
    dbsparql = client.ekeel
    # retrieve from mongodb collection=graphs the all elements with the value of video_id
    collection = dbsparql.graphs

    videoList = video_id_list.split(',')
    result_list=[]
    for i in range(0,len(videoList)):
        video_id = videoList[i]
        # initialize the dicitonary where we save our results
        result = {
            'video_id':video_id,
            'concept_starttime':[],
            'concept_endtime':[],
            'explain':[],
            'list_preconcept': [],
            'list_prenotes':[],
            'list_postnotes':[],
            'list_derivatedconcept':[],
            'derivatedconcept_starttime':[],
            'derivatedconcept_endtime':[]
            
        }

        #print("?????????????????????????????START??????????????????????????????????")
        #print("start query: ",video_id," ",concept_searched)
        #print("result: ",result)

        # two options:
        ## 1. search newest annotation
        ### 2. combine every annotation of a video into a unique graph and make the query of that
        cursor = collection.find({"video_id":video_id})
        optiongraph = 2
        gr=Graph()


        if optiongraph == 1:
            ## 1. search newest annotation
            ## search for the newest in term of timestamp and get the idx of the newest document
            ## maybe it's pointless if the lastest is always the newest
            ## but in case the order changes in the future, this piece of code will make the ode work right regardless
            lastest = "1970-01-01T00:00:00.000000Z"
            lastest_idx = 0
            for idx,document in enumerate(cursor):
                if document is None:
                    continue
                gr=Graph().parse(data=json.dumps(document["graph"]), format='json-ld')
                qr = """
                        PREFIX oa: <http://www.w3.org/ns/oa#>
                        PREFIX edu: <https://teldh.github.io/edurell#>
                        PREFIX dctypes: <http://purl.org/dc/dcmitype/>
                        PREFIX dcterms: <http://purl.org/dc/terms/>
                        
                        SELECT DISTINCT ?timestamp
                        WHERE {
                                ?who dcterms:created ?timestamp
                            }

                    """
                qres = gr.query(qr)
                #print("query result: ",qres)
                for row in qres:
                #   print("current_timestamp: ",lastest," / selected_timestamp: ",row['timestamp'])
                    if row['timestamp'] > lastest:
                        lastest = row['timestamp']
                        lastest_idx = idx
            #print("lastest_timestamp: ",lastest," lastest_idx: ",lastest_idx)
            #print("TESTTTTTTTTT       ",cursor)


            # select the newest document
            document = collection.find({"video_id":video_id})[lastest_idx]
            

            # Query the concept timeline and duration
            gr.parse(data=json.dumps(document["graph"]), format='json-ld')

            # initialize conceptVocabulary for the query
            gr.parse(data=json.dumps(document["conceptVocabulary"]), format='json-ld')

        else:
            ### 2. combine all annotation of a video together
            ### in mongodb we collect all annotation of a single video
            ### made by different people or the same
            ### this mode combine from the oldest to the newest into a single graph

            #print("start cursor for: ",video_id)
            for idx,document in enumerate(cursor):
            #   print("document ",video_id," idx: ",idx," \n\nGRAPH: ",document["graph"]," \n\nCONCEPT:  ",document["conceptVocabulary"]," \n\n")
            #  print("\n")
                # Query the concept timeline and duration
                if document["graph"]=="":
            #     print("\nIGNORE GRAPH: ")
                    continue
                if document["conceptVocabulary"] == "":
                #    print("\nIGNORE CONCEPT: ")

                    continue
                gr.parse(data=json.dumps(document["graph"]), format='json-ld')

                # initialize conceptVocabulary for the query
                
                gr.parse(data=json.dumps(document["conceptVocabulary"]), format='json-ld')

            


        ## --------------------------------------------------------------------------------------------------------------------------------------
        ## ---------------------------------------------------------QUERYCREATED-----------------------------------------------------------------
        ## --------------------------------------------------------------------------------------------------------------------------------------
        qr = """
                    PREFIX oa: <http://www.w3.org/ns/oa#>
                    PREFIX edu: <https://teldh.github.io/edurell#>
                    PREFIX dctypes: <http://purl.org/dc/dcmitype/>
                    PREFIX dcterms: <http://purl.org/dc/terms/>
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

                    SELECT DISTINCT ?created
                    WHERE{
                            ?who oa:motivatedBy oa:describing.
                            ?who dcterms:created ?created.
                            ?who a oa:Annotation.
                            ?who oa:hasBody ?c_id.
                            ?c_id skos:prefLabel ?c_selected.
                    }
        """

 
        qres = gr.query(qr, initBindings = {"c_selected":Literal(concept_searched, lang="en")})
        #print("query created")
        #print("qres: ",len(qres))
        for row in qres:
        #   print("_________________________________________")
        #  print(row['created'])
            result['created']=row['created']

        #print(result)



        ## --------------------------------------------------------------------------------------------------------------------------------------
        ## ---------------------------------------------------QUERYCONCEPTTIMELINE&SKOSNOTE------------------------------------------------------
        ## --------------------------------------------------------------------------------------------------------------------------------------
        qr = """
                    PREFIX oa: <http://www.w3.org/ns/oa#>
                    PREFIX edu: <https://teldh.github.io/edurell#>
                    PREFIX dctypes: <http://purl.org/dc/dcmitype/>
                    PREFIX dcterms: <http://purl.org/dc/terms/>
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                    SELECT ?concept_starttime ?concept_endtime ?explain
                    WHERE {
                            
                            ?who oa:hasBody ?c_id.
                            ?c_id skos:prefLabel ?c_selected.
                            ?who oa:motivatedBy oa:describing.
                            ?who oa:hasTarget ?target.
                            ?target oa:hasSelector ?selector.
                            ?selector oa:hasStartSelector ?startselector.
                            ?startselector rdf:value ?concept_starttime.
                            ?selector oa:hasEndSelector ?endselector.
                            ?endselector rdf:value ?concept_endtime.
                            ?who skos:note ?explain               
                        }


                """
    
        qres = gr.query(qr, initBindings = {"c_selected":Literal(concept_searched, lang="en")})

        #print("qres: ",len(qres))
        for row in qres:
            #print("result: ",row['concept_starttime']," ",row['concept_endtime'])
        #   print("_________________________________________")
        #  print(row['concept_starttime'],"\n",row['concept_endtime'])

            result['concept_starttime'].append(row['concept_starttime'])
            result['concept_endtime'].append(row['concept_endtime'])
            result['explain'].append(row['explain'])
        

        ## --------------------------------------------------------------------------------------------------------------------------------------
        ## ---------------------------------------------------------QUERYPRECONCEPTS-------------------------------------------------------------
        ## --------------------------------------------------------------------------------------------------------------------------------------
        ## preconcepts that aren't explained: no conceptDefinition nor conceptExpansion

        qr = """
                    PREFIX oa: <http://www.w3.org/ns/oa#>
                    PREFIX edu: <https://teldh.github.io/edurell#>
                    PREFIX dctypes: <http://purl.org/dc/dcmitype/>
                    PREFIX dcterms: <http://purl.org/dc/terms/>
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

                    SELECT DISTINCT ?preconcept ?prenote
                    WHERE{
                            ?who oa:hasBody ?preconceptIRI.
                            ?c_id skos:prefLabel ?c_selected.
                            ?who oa:motivatedBy edu:linkingPrerequisite.
                            ?who oa:hasTarget ?target.
                            ?target dcterms:subject ?c_id.
                            ?preconceptIRI skos:prefLabel ?preconcept.
                            ?who skos:note ?prenote.

                    }


        """


        qres = gr.query(qr, initBindings = {"c_selected":Literal(concept_searched, lang="en")})
        #print("preconcept")
        #print("qres: ",len(qres))
        for row in qres:
        #   print("a_________________________________________")
        #  print(row['preconcept'])
            result['list_preconcept'].append(row['preconcept'])
            result['list_prenotes'].append(row['prenote'])

        #print(result)

        
        ## --------------------------------------------------------------------------------------------------------------------------------------
        ## ---------------------------------------------------------QUERYCONCEPTDERIVATED--------------------------------------------------------
        ## --------------------------------------------------------------------------------------------------------------------------------------
        qr = """
                    PREFIX oa: <http://www.w3.org/ns/oa#>
                    PREFIX edu: <https://teldh.github.io/edurell#>
                    PREFIX dctypes: <http://purl.org/dc/dcmitype/>
                    PREFIX dcterms: <http://purl.org/dc/terms/>
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>

                    SELECT DISTINCT ?c_derivated ?postnote
                    WHERE{
                            ?who oa:hasBody ?c_id.
                            ?c_id skos:prefLabel ?c_selected.
                            ?who oa:motivatedBy edu:linkingPrerequisite.
                            ?who oa:hasTarget ?target.
                            ?target dcterms:subject ?c_derivatedIRI.
                            ?c_derivatedIRI skos:prefLabel ?c_derivated.
                            ?who skos:note ?postnote
                    }


        """
        """
            'list_derivatedconcept':[],
            'derivatedconcept_starttime':[],
            'derivatedconcept_endtime':[]
        """
        qres = gr.query(qr, initBindings = {"c_selected":Literal(concept_searched, lang="en")})
        #print("c_derivated")
        #print("qres: ",len(qres))
        for row in qres:
        #   print("b_________________________________________")
        #  print(row['c_derivated'])

            result['list_derivatedconcept'].append(row['c_derivated'])
            result['list_postnotes'].append(row['postnote'])

        




        for dc in result['list_derivatedconcept']:
            qr = """
                    PREFIX oa: <http://www.w3.org/ns/oa#>
                    PREFIX edu: <https://teldh.github.io/edurell#>
                    PREFIX dctypes: <http://purl.org/dc/dcmitype/>
                    PREFIX dcterms: <http://purl.org/dc/terms/>
                    PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
                    SELECT ?dc_starttime ?dc_endtime
                    WHERE {
                            
                            ?who oa:hasBody ?c_id.
                            ?c_id skos:prefLabel ?c_selected.
                            ?who oa:motivatedBy oa:describing.
                            ?who oa:hasTarget ?target.
                            ?target oa:hasSelector ?selector.
                            ?selector oa:hasStartSelector ?startselector.
                            ?startselector rdf:value ?dc_starttime.
                            ?selector oa:hasEndSelector ?endselector.
                            ?endselector rdf:value ?dc_endtime.               
                        }


                """
    
            qres = gr.query(qr, initBindings = {"c_selected":Literal(dc, lang="en")})
            #print("qres: ",len(qres))
            for row in qres:
                #print("result: ",row['concept_starttime']," ",row['concept_endtime'])
            #   print("_________________________________________")
            #  print(row['dc_starttime'],"\n",row['dc_endtime'])
                result['derivatedconcept_starttime'].append(row['dc_starttime'])
                result['derivatedconcept_endtime'].append(row['dc_endtime'])

        

        ## --------------------------------------------------------------------------------------------------------------------------------------
        ## ---------------------------------------------------------SLIDISHNESS------------------------------------------------------------------
        ## --------------------------------------------------------------------------------------------------------------------------------------
        VTS=VideoTextSegmentation.objects(video_id = video_id)
        for VTSdoc in VTS:
        # print(VTSdoc.video_id)
        # print(VTSdoc.slides_percentage)
            result['slides_percentage'] = str(VTSdoc.slides_percentage)
        result_list.append(result)

    
    return json.dumps(result_list)

@app.route('/api/testm/<video_id>')
@auth.login_required
def testm(video_id):
    """
    Test function for querying video data.

    Parameters
    ----------
    video_id : str
        Identifier for the video

    Returns
    -------
    dict
        Dictionary containing query results
    """
    client = pymongo.MongoClient(
        "mongodb+srv://"+MONGO_CLUSTER_USERNAME+":"+MONGO_CLUSTER_PASSWORD+"@clusteredurell.z8aeh.mongodb.net/edurell?retryWrites=true&w=majority")

    db = client.ekeel
    collection = db.graphs

    cursor = collection.find({"video_id": video_id})
    gr = Graph()
    retval={}
    for document in cursor:
        print("asd")
        if document is not None:
            
            gr.parse(data=json.dumps(document["graph"]), format='json-ld')


            qr = """
                PREFIX oa: <http://www.w3.org/ns/oa#>
                PREFIX edu: <https://teldh.github.io/edurell#>
                PREFIX dctypes: <http://purl.org/dc/dcmitype/>
                PREFIX dcterms: <http://purl.org/dc/terms/>
                
                SELECT ?sub ?pre ?obj
                WHERE {
                        ?sub ?pre ?obj
                    
                    }

            """

            qr2="""
                PREFIX oa: <http://www.w3.org/ns/oa#>
                PREFIX edu: <https://teldh.github.io/edurell#>
                PREFIX dctypes: <http://purl.org/dc/dcmitype/>
                PREFIX dcterms: <http://purl.org/dc/terms/>
                
                SELECT ?sub  ?obj
                WHERE {
                        ?sub dcterms:created ?obj
                    
                    }

            """
            qres = gr.query(qr)
            qres2=gr.query(qr2)
            resulto={}
            resulto2={}
            print("STARTOOOOOO ",qres)
            for idx,row in enumerate(qres):
                resulto[idx]={"subject":row['sub'],"predicate":row['pre'],"object":row['obj']}
            print("ENDOOOOOOOO")
            for idx,row in enumerate(qres2):
                resulto2[idx]={"subject":row['sub'],"object":row['obj']}
            retval["res"]=resulto
    return retval

@app.route('/api/sparql_query_concepts/<video_id>')
@auth.login_required
def sparql_query_concepts(video_id, annotator_id):
    """
    Perform SPARQL query for concepts.

    Parameters
    ----------
    video_id : str
        Identifier for the video
    annotator_id : str
        Identifier for the annotator
    """
    client = pymongo.MongoClient(
        "mongodb+srv://"+MONGO_CLUSTER_USERNAME+":"+MONGO_CLUSTER_PASSWORD+"@clusteredurell.z8aeh.mongodb.net/edurell?retryWrites=true&w=majority")

    db = client.ekeel
    collection = db.graphs

    query = {
        "annotator_id": annotator_id,
        "video_id": video_id
    }

    general_query = {
        "video_id": video_id
    }

    #se trova un grafo qualunque con quel video_id, salva il risultato della query
    if collection.find_one(general_query) is not None:
        risultato = collection.find_one(general_query)["conceptVocabulary"]
    #ma se trova il grafo con quel video_id e proprio con quell'annotator_id, sovrascrive risultato
    if collection.find_one(query) is not None:
        risultato = collection.find_one(query)["conceptVocabulary"]    

    #se almeno una delle due query è andata a buon fine
    if risultato is not None:
        gr = Graph()\
        .parse(data=json.dumps(risultato), format='json-ld')

        tic = time.time()

        # Seleziona tutti i nodi concetto ed eventuali sinonimi
        query3 = """
            PREFIX oa: <http://www.w3.org/ns/oa#>
            PREFIX edu: <https://teldh.github.io/edurell#>
            PREFIX dctypes: <http://purl.org/dc/dcmitype/>
            
            SELECT ?concept ?synonym
            WHERE {
                    ?concetto skos:prefLabel ?concept.
                    OPTIONAL {
                        ?concetto skos:altLabel ?synonym
                    }
                    FILTER (!BOUND(?altLabel))
                }"""

        qres = gr.query(query3)

        toc = time.time()

        #print per i concetti
        print("Results: - obtained in %.4f seconds" % (toc - tic))
        for row in qres: 
            print(f"Concept: {row.concept} || Synonym: {row.synonym}")


def sparql_query_prerequisite(video_id, annotator_id):
    """
    Perform SPARQL query for prerequisites.

    Parameters
    ----------
    video_id : str
        Identifier for the video
    annotator_id : str
        Identifier for the annotator
    """
    client = pymongo.MongoClient(
        "mongodb+srv://"+MONGO_CLUSTER_USERNAME+":"+MONGO_CLUSTER_PASSWORD+"@clusteredurell.z8aeh.mongodb.net/edurell?retryWrites=true&w=majority")

    db = client.ekeel
    collection = db.graphs

    query = {
        "annotator_id": annotator_id,
        "video_id": video_id
    }

    general_query = {
        "video_id": video_id
    }

    #se trova un grafo qualunque con quel video_id, salva il risultato della query
    if collection.find_one(general_query) is not None:
        risultato = collection.find_one(general_query)["graph"]
    #ma se trova il grafo con quel video_id e proprio con quell'annotator_id, sovrascrive risultato
    if collection.find_one(query) is not None:
        risultato = collection.find_one(query)["graph"]    

    #se almeno una delle due query è andata a buon fine
    if risultato is not None:
        gr = Graph()\
        .parse(data=json.dumps(risultato), format='json-ld')

        tic = time.time()

        #query per i prerequisiti
        query2 = """
            PREFIX oa: <http://www.w3.org/ns/oa#>
            PREFIX edu: <https://teldh.github.io/edurell#>

            SELECT ?prerequisite_concept ?created ?creator ?prerequisite_type ?target_concept
            WHERE {
                    ?concept_prerequisite oa:motivatedBy edu:linkingPrerequisite.
                    ?concept_prerequisite dcterms:created ?created.
                    ?concept_prerequisite dcterms:creator ?creator.
                    ?concept_prerequisite oa:hasBody ?prerequisite_concept.
                    ?concept_prerequisite skos:note ?prerequisite_type.
                    ?concept_prerequisite oa:hasTarget ?target.
                    ?target dcterms:subject ?target_concept.
                }"""


        qres = gr.query(query2)

        toc = time.time()

        #print per i prerequisiti
        print("Results: - obtained in %.4f seconds" % (toc - tic))
        for row in qres: 
            print(f"Prerequisite concept: {row.prerequisite_concept}")
            print(f"Created: {row.created}")
            print(f"Creator: {row.creator}")
            print(f"Prerequisite Type: {row.prerequisite_type}")
            print(f"Target concept: {row.target_concept}")


def sparql_query_definitions(video_id, annotator_id):
    """
    Perform SPARQL query for definitions.

    Parameters
    ----------
    video_id : str
        Identifier for the video
    annotator_id : str
        Identifier for the annotator
    """
    client = pymongo.MongoClient(
        "mongodb+srv://"+MONGO_CLUSTER_USERNAME+":"+MONGO_CLUSTER_PASSWORD+"@clusteredurell.z8aeh.mongodb.net/edurell?retryWrites=true&w=majority")

    db = client.ekeel
    collection = db.graphs

    query = {
        "annotator_id": annotator_id,
        "video_id": video_id
    }

    general_query = {
        "video_id": video_id
    }

    #se trova un grafo qualunque con quel video_id, salva il risultato della query
    if collection.find_one(general_query) is not None:
        risultato = collection.find_one(general_query)["graph"]
    #ma se trova il grafo con quel video_id e proprio con quell'annotator_id, sovrascrive risultato
    if collection.find_one(query) is not None:
        risultato = collection.find_one(query)["graph"]    

    #se almeno una delle due query è andata a buon fine
    if risultato is not None:
        gr = Graph()\
        .parse(data=json.dumps(risultato), format='json-ld')

        tic = time.time()

        # Seleziona i concetti che sono spiegati nel video
        query1 = """
            PREFIX oa: <http://www.w3.org/ns/oa#>
            PREFIX edu: <https://teldh.github.io/edurell#>
            PREFIX dctypes: <http://purl.org/dc/dcmitype/>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>

            SELECT ?explained_concept ?created ?creator ?description_type
            WHERE {
                    ?concept_definition oa:motivatedBy oa:describing.
                    ?concept_definition dcterms:created ?created.
                    ?concept_definition dcterms:creator ?creator.
                    ?concept_definition oa:hasBody ?explained_concept.
                    ?concept_definition skos:note ?description_type.
                    ?concept_definition oa:hasTarget ?target.
                    ?target oa:hasSelector ?selector.
                    ?selector oa:hasStartSelector ?startSelector

                }"""


        qres = gr.query(query1)

        toc = time.time()
        
        #print per le definizioni
        print("Results: - obtained in %.4f seconds" % (toc - tic))
        for row in qres:
            print(f"Explained concept: {row.explained_concept}")
            print(f"Created: {row.created}")
            print(f"Creator: {row.creator}")
            print(f"Description Type: {row.description_type}")




if __name__ == '__main__':
    """
    Main entry point for the Flask application.
    """
    print("***** EKEEL - Video Augmentation: main.py::__main__: Inizio ******")

    

    print("***** EKEEL - Video Augmentation: main.py::__main__: Fine ******")

    app.run(debug=False)



# authentication system made with this tutorial : https://blog.miguelgrinberg.com/post/restful-authentication-with-flask
