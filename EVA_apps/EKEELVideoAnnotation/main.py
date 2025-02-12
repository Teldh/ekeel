"""
EKEEL Video Annotation Server Backend

This module implements a Flask web server for video annotation and analysis.
It provides functionality for:

- User Management:
    * Registration and authentication
    * Profile management
    
- Video Processing:
    * YouTube video processing
    * Transcript extraction
    * Video segmentation
    
- Annotation Features:
    * Manual concept mapping
    * Definition creation
    * Vocabulary management
    
- Analysis Tools:
    * Burst analysis (automatic/semi-automatic)
    * Inter-annotator agreement
    * Gold standard creation
    * Linguistic analysis
    
- Data Management:
    * MongoDB storage integration
    * JSON-LD export format
    * SKOS vocabulary support

"""

from flask import render_template, jsonify, request, flash, redirect, url_for
from flask_login import current_user, login_user, logout_user, login_required
#from werkzeug.urls import url_parse
from urllib.parse import urlparse
import bcrypt
import random
import string
import json
from datetime import datetime, timezone


from text_processor.conll import get_text
from burst.prototype import burst_extraction, burst_extraction_with_synonyms, convert_to_skos_concepts
from metrics.metrics import calculate_metrics
from config import app
import database.mongo as mongo
from database.mongo import users, unverified_users
from media.segmentation import VideoAnalyzer, SemanticText
from ontology.rdf_graph import annotations_to_jsonLD
from burst.prototype import create_local_vocabulary, create_burst_graph
from forms.form import addVideoForm, RegisterForm, LoginForm, GoldStandardForm, ForgotForm, PasswordResetForm, ConfirmCodeForm, BurstForm
from text_processor.words import get_real_keywords
from text_processor.conll import conll_gen, html_interactable_transcript_legacy, html_interactable_transcript_word_level
from metrics.analysis import compute_data_summary, compute_agreement, linguistic_analysis, fleiss
from metrics.agreement import create_gold
from forms.user import User
from forms.mail import send_mail, generate_confirmation_token, confirm_token, send_confirmation_mail
from text_processor.synonyms import create_skos_dictionary, get_synonyms_from_list
from text_processor.words import NLPSingleton


#video_segmentations_queue = Manager().list()
#workers_queue_scheduler(video_segmentations_queue)

@app.route('/')
def index():
    """
    Render the index page.

    Returns
    -------
    str
        The rendered HTML content of the index page.
    """
    return render_template('index.html')


@app.route('/login', methods=['POST', 'GET'])
def login():
    """
    Handle the login process for users.

    Returns
    -------
    str
        The rendered HTML content of the login page if the user is not authenticated or the form is not submitted/valid.
    werkzeug.wrappers.Response
        A redirect response to the next page if the user is authenticated or the form is submitted and valid.
    """
    form = LoginForm()

    if current_user.is_authenticated:
        next_page = url_for('index')
        return redirect(next_page)

    if form.is_submitted():
        if form.validate():
            user = User(form.email.data)
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for('index')
            return redirect(next_page)

    return render_template('user/login.html', form=form)


@app.route('/logout')
def logout():
    """
    Handle the logout process for users.

    Returns
    -------
    str
        The rendered HTML content of the index page after logging out the user.
    """
    logout_user()
    return render_template('index.html')


@app.route('/register', methods=['POST', 'GET'])
def register():
    """
    Handle the registration process for new users.

    Returns
    -------
    str
        The rendered HTML content of the registration page if the form is not submitted/valid.
    werkzeug.wrappers.Response
        A redirect response to the confirmation code page if the form is submitted and valid.
    """
    print("***** EKEEL - Video Annotation: db_mongo.py::register() ******")

    form = RegisterForm()
    if form.validate_on_submit():
        password = bcrypt.hashpw(form.password.data.encode('utf-8'), bcrypt.gensalt())
        password_hash = password.decode('utf8')

        # generate a random string of lenght N composed of lowercase letters and numbers

        code = ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(6)).upper()
        hashed_code = bcrypt.hashpw(code.encode('utf-8'), bcrypt.gensalt())
        code_on_creation_hash = hashed_code.decode('utf8')

        new_user = {
            'name': form.name.data,
            'surname': form.surname.data,
            'email': form.email.data,
            'password_hash': password_hash,
            'code_on_creation_hash': code_on_creation_hash,
            'nb_try_code_on_creation': 0
        }

        unverified_users.insert_one(new_user)

        send_confirmation_mail(form.email.data, code)


        mail = json.dumps(form.email.data)
        next_page = url_for('confirm_code', mail=mail)
        return redirect(next_page)

    return render_template('user/register.html', form=form)


@app.route('/confirm_code', methods=['POST', 'GET'])
def confirm_code():
    """
    Handle the confirmation code process for new users.

    Returns
    -------
    str
        The rendered HTML content of the confirmation code page if the form is not submitted/valid.
    werkzeug.wrappers.Response
        A redirect response to the login page if the confirmation code is valid.
    """
    print("***** EKEEL - Video Annotation: db_mongo.py::confirm_code() ******")

    form = ConfirmCodeForm()
    email = json.loads(request.args['mail'])
    
    if form.validate_on_submit():

        code = form.code.data

        user = unverified_users.find_one({"email": email})

        if bcrypt.checkpw(code.encode('utf-8'), user["code_on_creation_hash"].encode('utf-8')):

            new_user = {
                'name': user["name"],
                'surname': user["surname"],
                'email': user["email"],
                'password_hash': user["password_hash"],
                'video_history_list': []
            }
            # users.insert_one(new_user)
            unverified_users.delete_one({"email": email})
            users.insert_one(new_user)

            flash('Thanks! Email confirmed, you can now log in', 'success')

        else:
            tries = user["nb_try_code_on_creation"] + 1
            new = {"$set": {"nb_try_code_on_creation": tries}}
            unverified_users.update_one({"email": email}, new)


    return render_template('user/confirm_code.html', form=form)



@app.route('/confirm/<token>')
def confirm_email(token):
    """
    Handle the email confirmation process for new users.

    Parameters
    ----------
    token : str
        The confirmation token sent to the user's email.

    Returns
    -------
    str
        The rendered HTML content of the index page after confirming the email.
    """
    print("***** EKEEL - Video Annotation: db_mongo.py::confirm_email() ******")

    try:
        print(token)
        email = confirm_token(token)

        u = unverified_users.find_one({"email": email})
        new_user = {
            'name': u["name"],
            'surname': u["surname"],
            'email': u["email"],
            'password_hash': u["password_hash"],
            'video_history_list': []
        }
        # users.insert_one(new_user)
        unverified_users.delete_one({"email": email})
        users.insert_one(new_user)

        us = User(email)
        login_user(us)

        flash('Thanks! Email confirmed', 'success')
    except:
        flash('The confirmation link is invalid or has expired.', 'danger')

    return render_template('index.html')



@app.route('/forgot_password', methods=['POST', 'GET'])
def forgot_password():
    """
    Handle the forgot password process for users.

    Returns
    -------
    str
        The rendered HTML content of the forgot password page if the form is not submitted/valid.
    werkzeug.wrappers.Response
        A redirect response to the password reset page if the form is submitted and valid.
    """
    print("***** EKEEL - Video Annotation: db_mongo.py::forgot_password() ******")

    form = ForgotForm()

    if form.validate_on_submit():
        token = generate_confirmation_token(form.email.data)
        reset_url = url_for('password_reset', token=token, _external=True)
        html = render_template('user/user_forgot_password_mail.html', reset_url=reset_url)
        subject = "Password reset"

        send_mail(form.email.data, subject, html)
        flash('Email sent to ' + form.email.data, 'success')

    return render_template('user/forgot_password.html', form=form)



@app.route('/password_reset/<token>', methods=['POST', 'GET'])
def password_reset(token):
    """
    Handle the password reset process for users.

    Parameters
    ----------
    token : str
        The password reset token sent to the user's email.

    Returns
    -------
    str
        The rendered HTML content of the password reset page if the form is not submitted/valid.
    werkzeug.wrappers.Response
        A redirect response to the index page if the token is invalid or expired.
    """
    print("***** EKEEL - Video Annotation: db_mongo.py::password_reset() ******")

    form = PasswordResetForm()

    try:
        email = confirm_token(token)

        if form.validate_on_submit():
            hashpass = bcrypt.hashpw(form.password.data.encode('utf-8'), bcrypt.gensalt())
            password_hash = hashpass.decode('utf8')
            mongo.reset_password(email, password_hash)
            flash('Password updated', 'success')

        return render_template('user/password_reset.html', form=form)

    except:
        flash('The link is invalid or has expired.', 'danger')
        return render_template('index.html')




@app.route('/video_selection', methods=['GET', 'POST'])
@login_required
def video_selection():
    """
    Handle video selection and processing for annotation purposes.

    This function manages the video selection interface and processes new video submissions.
    It handles both GET requests to display the video selection page and POST requests to 
    process new video submissions. For new videos, it:
    
    - Downloads the video
    
    - Extracts and processes the transcript
    
    - Segments the video
    
    - Creates thumbnails
    
    - Processes concepts and vocabulary based on user selection (edit his own or last annotator's annotations)
    
    - Sets up the annotation environment

    Parameters
    ----------
    url : str
        URL of the video to be processed (from addVideoForm)

    Returns
    -------
    str
        On GET or failed form validation: renders video_selection.html template
        showing existing videos and upload form
    werkzeug.wrappers.Response
        On successful POST: renders mooc_annotator.html template with processed
        video data and annotation interface
        
    """
    print("***** EKEEL - Video Annotation: main.py::video_selection(): Inizio ******")
    form = addVideoForm()
    videos = mongo.get_videos(["video_id","title", "creator"])

    if not form.validate_on_submit():
        for video in videos:
            annotations = mongo.get_annotation_infos(video["video_id"], 
                                                     ["annotator_name", "annotator_id", "last_modification", "annotation_completed"])
            status = "None"
            for annotation in annotations:
                if annotation["annotator_id"] == current_user.mongodb_id:
                    status = "Completed" if annotation["annotation_completed"] else "In Progress"
                annotation.pop("annotator_id")
            video["my_annotation_status"] = status
            video["has_annotation"] = "True" if any(annotations) else "False"
        return render_template('video_selection.html', form=form, videos=videos)
    
    try:
        url = form.url.data
        vid_analyzer = VideoAnalyzer(url)
        vid_analyzer.download_video()
        
        # NOTE extracting transcript from audio with whisper on high-end i9 8 core process at ~1.3 sec/s
        vid_analyzer.request_transcript()
        vid_analyzer.analyze_transcript()
        vid_analyzer.request_terms()
        vid_analyzer.filter_terms()
        vid_analyzer.transcript_segmentation()
        vid_analyzer.create_thumbnails()
        #vid_analyzer.analyze_video()  for now we don't extract slides
        video_id = vid_analyzer.video_id
        data = vid_analyzer.data
        
        language = vid_analyzer.identify_language()
        text = SemanticText(" ".join(timed_sentence["text"] for timed_sentence in data["transcript_data"]["text"] if not "[" in timed_sentence['text']), language)
        conll_sentences = conll_gen(video_id,text,language)
        if vid_analyzer.data["transcript_data"]["is_whisper_transcribed"]:
            #lemmatized_subtitles, all_lemmas = html_interactable_transcript_word_level(data["transcript_data"]["text"], language)
            #all_lemmas = vid_analyzer.data["transcript_data"]["lemmas"]
            lemmatized_subtitles = html_interactable_transcript_word_level(data["transcript_data"]["text"])
        else:
            lemmatized_subtitles, all_lemmas = html_interactable_transcript_legacy(data["transcript_data"]["text"], conll_sentences, language)
        
        if form.annotator.data == "self":
        
            annotator = current_user.complete_name
            relations = mongo.get_concept_map(current_user.mongodb_id, video_id)
            definitions = mongo.get_definitions(current_user.mongodb_id, video_id)
            annotation_status = mongo.get_annotation_status(current_user.mongodb_id, video_id)
            marked_completed = any(annotation_status) and annotation_status["annotation_completed"]
            
            
            # Obtaining concept vocabulary from DB
            conceptVocabulary  = mongo.get_vocabulary(current_user.mongodb_id, video_id)
        
        elif form.annotator.data == "last" or True: # default to last annotator
            annotations = mongo.get_annotation_infos(video_id, 
                                                     ["annotator_name", "annotator_id", "last_modification", "annotation_completed"])
            annotations.sort(key=lambda x: x["last_modification"], reverse=True)
            last_annotator = annotations[0]
            relations = mongo.get_concept_map(last_annotator["annotator_id"], video_id)
            definitions = mongo.get_definitions(last_annotator["annotator_id"], video_id)
            annotation_status = mongo.get_annotation_status(last_annotator["annotator_id"], video_id)
            marked_completed = any(annotation_status) and annotation_status["annotation_completed"]
            
            # Obtaining concept vocabulary from DB
            conceptVocabulary  = mongo.get_vocabulary(last_annotator["annotator_id"], video_id)
            annotator = last_annotator["annotator_name"]
        
        # If the concept vocabulary is in the DB then initialize concept to the ones of the vocabulary
        if conceptVocabulary is not None:
            conceptVocabulary = {key:value for key,value in conceptVocabulary.items()}
            lemmatized_concepts = []
            sem_text = SemanticText("",language)
            for concept in conceptVocabulary.keys():
                lemmatized_concepts.append(sem_text.set_text(concept).get_semantic_structure_info())
        
        # If the concept vocabulary is new (empty) in DB then initialize it from the terms extracted
        if conceptVocabulary is None:
            lemmatized_concepts = [SemanticText(term["term"].lower() if term["term"].istitle() else term["term"],language).get_semantic_structure_info() for term in vid_analyzer.data["transcript_data"]["terms"]]
            #-----------------------------------------------------------------
            # 1) Automatically obtain synonyms using wordnet NLTK
            #
            #conceptVocabulary = get_synonyms_from_list(lemmatized_concepts)
            # 2) Start with empty synonyms in concept vocabulary
            #
            conceptVocabulary = {}
            for concept in lemmatized_concepts :
                conceptVocabulary[concept["text"]] = []
            #-----------------------------------------------------------------
        # This shouldn't happen but in case of different versions of annotations is kept for compatibility
        for rel in relations:
            if rel["prerequisite"] not in conceptVocabulary.keys():
                lemmatized_concepts.append(SemanticText(rel["prerequisite"],language).get_semantic_structure_info())
            if rel["target"] not in conceptVocabulary.keys():
                lemmatized_concepts.append(SemanticText(rel["target"],language).get_semantic_structure_info())
        
        NLPSingleton().destroy()  
                
        return render_template('mooc_annotator.html', 
                               result=data["transcript_data"]["text"], video_id=video_id, start_times=list(map(lambda x: x[0],data["video_data"]["segments"])),
                               images_path=vid_analyzer.images_path, concepts=lemmatized_concepts,is_temp_transcript=not data["transcript_data"]["is_whisper_transcribed"],
                               video_duration=data['duration'], lemmatized_subtitles=lemmatized_subtitles, annotator=annotator, language=language, is_completed=marked_completed,
                               conceptVocabulary=conceptVocabulary, title=data['title'], relations=relations, definitions=definitions)
    except Exception as e:
        import sys
        import os
        import traceback
    
        tb_details = traceback.extract_tb(sys.exc_info()[2])

        print(f"\033[91mException in video selection: {e}\033[0m")
        for frame in tb_details:
            filename = os.path.basename(frame.filename)
            # Read the specific line of code
            line_number = frame.lineno
            with open(frame.filename, 'r') as f:
                lines = f.readlines()
                error_line = lines[line_number - 1].strip()
            print(f"\033[91mFile: {filename}, Function: {frame.name}, Line: {line_number} | {error_line}\033[0m")
        flash(e, "Danger")

    print("***** EKEEL - Video Annotation: main.py::video_selection(): Fine ******")

    return render_template('video_selection.html', form=form, videos=videos)


@app.route('/get_concept_vocabulary', methods=["GET", "POST"])
def get_concept_vocabulary():
    """
    Retrieve concept vocabulary and their synonyms.

    This endpoint handles requests to get synonyms for a list of concepts using NLTK Wordnet.
    Accepts POST requests with JSON data containing concepts and returns a vocabulary mapping.

    Parameters
    ----------
    concepts : list
        List of concept strings to find synonyms for, passed in request JSON

    Returns
    -------
    dict
        JSON response containing:
        - conceptVocabulary : dict
            Mapping of concepts to their synonyms from Wordnet
    """
    print("***** EKEEL - Video Annotation: main.py::get_concept_vocabulary() ******")

    data = request.json

    # Getting concepts:
    concepts = data["concepts"]
    # Finding synonyms with NLTK Wordnet:
    conceptVocabulary = get_synonyms_from_list(concepts)

    json = {
        #"concepts": concepts,
        "conceptVocabulary": conceptVocabulary
    }

    return json


@app.route('/upload_graph', methods=["GET", "POST"])
def upload_annotated_graph():
    """
    Upload and store annotated concept graph in JSON-LD format.
    The annotator can be anyone based on the provided name.

    This endpoint receives annotation data for a video, converts it to JSON-LD format,
    and stores it in MongoDB. The annotations include concept relationships, vocabulary,
    and metadata about the annotation process.

    Parameters
    ----------
    annotations : dict
        JSON data containing:
        - id : str
            Video identifier
        - conceptVocabulary : dict
            Mapping of concepts to synonyms
        - language : str
            Language of annotations
        - is_completed : bool
            Whether annotation is complete

    Returns
    -------
    dict
        JSON response containing:
        - done : bool
            True if upload successful, False if error occurred
    """
    print("***** EKEEL - Video Annotation: main.py::upload_annotations(): Inizio ******")
    annotations = request.json
    annotator_name = annotations["annotator"]
    annotator = users.find_one({"name": annotator_name.split()[0], "surname": annotator_name.split()[1]})
    if not annotator:
        return {"done": False}

    _, data = annotations_to_jsonLD(annotations, isAutomatic=False)

    data["video_id"] = annotations["id"]
    data["annotator_id"] = str(annotator["_id"])
    data["annotator_name"] = annotator["name"] + " " + annotator["surname"]
    data["email"] = annotator["email"]
    data["conceptVocabulary"] = create_skos_dictionary(annotations["conceptVocabulary"], annotations["id"], "manu", annotations["language"])
    data["annotation_completed"] = annotations["is_completed"]
    data["last_modification"] = datetime.now(timezone.utc).isoformat() + 'Z'

    data["graph"]["@graph"].extend([{"id": x["id"], "type": "skos:Concept"} for x in data["conceptVocabulary"]["@graph"]])

    # inserting annotations on DB
    try:
        mongo.insert_graph(data)
    except Exception as e:
        print(e)
        flash(e, "error")
        return {"done": False}

    print("***** EKEEL - Video Annotation: main.py::upload_annotations(): Fine ******")
    return {"done": True}


# download graph on the manual annotator side
@app.route('/download_graph', methods=["GET", "POST"])
def prepare_annotated_graph():
    """
    Prepare concept graph annotations for download in JSON-LD format.

    This endpoint receives annotation data, converts it to JSON-LD format with SKOS vocabulary,
    and prepares it for client-side download. The function creates a collection of concepts
    and their relationships in a standardized semantic web format.

    Parameters
    ----------
    annotations : dict
        JSON data containing:
        - id : str
            Video identifier 
        - conceptVocabulary : dict
            Dictionary mapping concepts to their vocabulary
        - language : str
            Language code for the annotations

    Returns
    -------
    dict
        JSON-LD formatted data containing:
        - @context : dict
            JSON-LD context definitions
        - @graph : list
            List of nodes in the concept graph including:
            - Concept definitions
            - Relationships
            - SKOS vocabulary collection
    """
    print("***** EKEEL - Video Annotation: main.py::download_graph(): Inizio ******")

    annotations = request.json

    _, json = annotations_to_jsonLD(annotations,isAutomatic=False)

    conceptVocabulary = create_skos_dictionary(annotations["conceptVocabulary"], annotations["id"], "manu", annotations["language"])
    
    json["graph"]["@graph"].append({ "id":"localVocabulary","type": "skos:Collection","skos:member": [elem for elem in conceptVocabulary["@graph"]]})

    result = {
        "@context": conceptVocabulary["@context"],
        "@graph": json["graph"]["@graph"]
    }

    print("***** EKEEL - Video Annotation: main.py::download_annotated_graph(): Fine ******")
    # real download happens on the js side
    return result   
  
@app.route('/delete_video', methods=["GET", "POST"])
def delete_video():
    """
    Delete a video and its associated data from the database.

    This endpoint handles video deletion requests. It removes the video entry
    and all associated annotations from MongoDB storage.

    Parameters
    ----------
    video_id : str
        Unique identifier of the video to delete, passed in request JSON

    Returns
    -------
    dict
        JSON response containing:
        - done : bool
            True if deletion successful, False if error occurred
    """
    video_id = request.json["video_id"]
    mongo.remove_video(video_id)
    return {"done":True}

@app.route("/delete_annotation", methods=["GET","POST"])
def delete_annotation():
    """
    Delete user-specific annotations for a video.

    This endpoint removes all annotation data associated with a specific video
    and user combination from the database.

    Parameters
    ----------
    video_id : str
        Unique identifier of the video whose annotations should be deleted
    user : dict
        Dictionary containing user information:
        - id : str
            MongoDB user identifier
        - name : str 
            User's full name

    Returns
    -------
    dict
        JSON response containing:
        - done : bool
            True if deletion successful, False if error occurred
    """
    video_id = request.json["video_id"]
    user = {"id": current_user.mongodb_id,
            "name": current_user.complete_name}
    mongo.remove_annotations_data(video_id, user)
    
    return {"done":True}
    

@app.route('/analysis', methods=['GET', 'POST'])
@login_required
def analysis():
    """
    Handle various types of annotation analysis requests.

    This endpoint processes different types of analysis on video annotations:
    - Data summary: Statistical analysis of concept maps and definitions
    - Agreement: Compare annotations between two annotators
    - Linguistic: Analyze linguistic properties of annotations
    - Fleiss: Calculate inter-annotator agreement using Fleiss' kappa

    Parameters
    ----------
    analysis_type : str
        Type of analysis to perform:
        - 'data_summary': Statistical summary
        - 'agreement': Inter-annotator comparison
        - 'linguistic': Linguistic analysis
        - 'fleiss': Fleiss' kappa calculation
    video : str
        Video identifier for analysis
    annotator : str, optional
        Annotator ID for data_summary and linguistic analysis
    annotator1 : str, optional
        First annotator ID for agreement analysis
    annotator2 : str, optional
        Second annotator ID for agreement analysis

    Returns
    -------
    str
        Rendered HTML template with analysis results:
        - On GET: analysis_selection.html with video choices
        - On POST: analysis_results.html with computed results
    """
    print("***** EKEEL - Video Annotation: db_mongo.py::analysis() ******")

    video_choices = mongo.get_graphs_info()

    if request.method == 'POST':
        analysis_type = request.form["analysis_type"]

        if analysis_type == "data_summary":
            video_id = request.form["video"]
            annotator_id = request.form["annotator"]

            concept_map = mongo.get_concept_map(annotator_id, video_id)
            definitions = mongo.get_definitions(annotator_id, video_id)

            results = compute_data_summary(video_id,concept_map, definitions)

            if annotator_id != "Burst_Analysis":
                user = mongo.get_user(annotator_id)
                annotator = user["name"] + " " + user["surname"]

            else:
                annotator = "Burst"

            return render_template('analysis_results.html', results=results, annotator=annotator, title=video_choices[video_id]["title"])

        elif analysis_type == "agreement":
            video_id = request.form["video"]
            annotator1_id = request.form["annotator1"]
            annotator2_id = request.form["annotator2"]

            concept_map1 = mongo.get_concept_map(annotator1_id, video_id)
            concept_map2 = mongo.get_concept_map(annotator2_id, video_id)

            results = compute_agreement(concept_map1, concept_map2)

            if annotator1_id != "Burst_Analysis":
                u1 = mongo.get_user(annotator1_id)
                results["annotator1"] = u1["name"] + " " + u1["surname"]
            else:
                results["annotator1"] = "Burst"

            if annotator2_id != "Burst_Analysis":
                u2 = mongo.get_user(annotator2_id)
                results["annotator2"] = u2["name"] + " " + u2["surname"]
            else:
                results["annotator2"] = "Burst"


            return render_template('analysis_results.html', results=results, title=video_choices[video_id]["title"])

        elif analysis_type == "linguistic":
            video_id = request.form["video"]
            annotator_id = request.form["annotator"]

            results = linguistic_analysis(annotator_id, video_id)

            return render_template('analysis_results.html', results=results, title=video_choices[video_id]["title"])


        elif analysis_type == "fleiss":
            video_id = request.form["video"]

            results = fleiss(video_id)

            return render_template('analysis_results.html', results=results, analysis_type=analysis_type,
                                   title=video_choices[video_id]["title"])

    videos = []
    for vid_id in video_choices.keys():
        video = video_choices[vid_id]
        video["video_id"] = vid_id
        videos.append(video)
    
    return render_template('analysis_selection.html',  videos=videos) #form=form,


@app.route('/gold_standard', methods=['GET', 'POST'])
@login_required
def gold_standard():
    """
    Create gold standard annotations from multiple annotators' work.

    This endpoint handles the creation of consensus annotations by combining
    the work of multiple annotators based on agreement thresholds.

    Parameters
    ----------
    video : str
        Selected video identifier from form
    annotators : list
        List of selected annotator IDs from form
    agreements : float
        Agreement threshold for including annotations in gold standard
    name : str
        Name for the gold standard annotation set

    Returns
    -------
    str
        Rendered HTML template 'gold_standard.html' containing:
        - video_choices : dict
            Available videos and their metadata
        - form : GoldStandardForm
            Form for gold standard creation parameters
    """
    print("***** EKEEL - Video Annotation: db_mongo.py::gold_standard() ******")

    form = GoldStandardForm()

    video_choices = mongo.get_graphs_info()
    form.video.choices = [(c, video_choices[c]["title"]) for c in video_choices]

    # WTFORM impone che tutte le scelte siano definite prima, quindi metto tutti gli annotatori possibili,
    # verranno poi filtrati cliccando il video

    for v in video_choices:
        for annotator in video_choices[v]["annotators"]:
            choice = (annotator["id"], annotator["name"])
            if choice not in form.annotators.choices:
                form.annotators.choices.append(choice)

    if form.validate_on_submit():
        create_gold(form.video.data, form.annotators.data, form.agreements.data, form.name.data)

    return render_template('gold_standard.html',  video_choices=video_choices, form=form)



@app.route('/burst', methods=['GET', 'POST'])
@login_required
def burst():
    """
    Process burst analysis requests for video annotations.

    This endpoint handles burst analysis of videos, which can be either:
    - Semi-automatic: Extracts transcript and processes text for annotations
    - Automatic: Extracts keywords only

    Parameters
    ----------
    url : str
        YouTube video ID from form
    type : str
        Analysis type from form:
        - 'semi': Semi-automatic analysis with transcript
        - 'auto': Automatic analysis with keywords only

    Returns
    -------
    str
        On GET: 
            Rendered 'burst.html' template with:
            - form : BurstForm
                Form for burst analysis parameters
            - videos : list
                Available videos for analysis
        On POST:
            Rendered 'burst_results.html' template with:
            - result : list
                Processed subtitles (semi-automatic only)
            - video_id : str
                YouTube video identifier
            - language : str
                Detected video language
            - concepts : list
                Extracted keywords
            - title : str
                Video title
            - lemmatized_subtitles : list
                Processed subtitle text (semi-automatic only)
            - type : str
                Analysis type performed
    """
    print("***** EKEEL - Video Annotation: db_mongo.py::burst() ******")

    #form = addVideoForm()
    form = BurstForm()
    videos = mongo.get_videos(["video_id","title", "creator"])

    if form.validate_on_submit():

        video_id = form.url.data
        video = VideoAnalyzer(f"https://youtu.be/{video_id}",{"language","transcript_data"})
        #text = SemanticText(get_text(video_id), video.identify_language())      
        #conll_sentences = conll_gen(video_id, text)
        title, keywords = get_real_keywords(video_id,annotator_id = current_user.mongodb_id)
            
        # semi-automatic extraction
        if form.type.data == "semi":

            video.request_transcript()
            subtitles = video.data["transcript_data"]["text"]
            #if video.data["transcript_data"]["is_whisper_transcribed"]:
            #all_lemmas = set(video._get_words_lemma().values())
            lemmatized_subtitles = html_interactable_transcript_word_level(subtitles)
            #else:
            #    lemmatized_subtitles, all_lemmas = html_interactable_transcript_legacy(subtitles,video.data["language"], concepts=keywords)

            return render_template('burst_results.html', result=subtitles, video_id=video_id, language=video.data["language"], concepts=keywords,
                                   title=title, lemmatized_subtitles=lemmatized_subtitles, type="semi")

        return render_template('burst_results.html', result=[], video_id=video_id,language=video.data["language"], concepts=keywords, title=title,
                                lemmatized_subtitles=[], type=form.type.data)

    return render_template('burst.html', form=form, videos=videos)



@app.route('/burst_launch', methods=["GET", "POST"])
def burst_launch():
    """
    Process and store burst analysis results with optional synonym expansion.

    This endpoint handles the processing of burst analysis results, storing them
    in the database, and computing comparison metrics with existing annotations.

    Parameters
    ----------
    data : dict
        JSON request data containing:
        - id : str
            Video identifier
        - concepts : list
            List of extracted concepts
        - conceptVocabulary : dict
            Mapping of concepts to synonyms
        - syn_burst : bool
            Whether to include synonym expansion
        - burst_type : str
            Type of burst analysis ('auto' or 'semi')

    Returns
    -------
    dict
        JSON response containing:
        - concepts : list
            Processed concept list
        - concept_map : dict
            Generated concept relationships
        - definitions : dict
            Concept definitions
        - data_summary : dict
            Statistical summary of results
        - downloadable_jsonld_graph : dict
            JSON-LD formatted graph data
        - agreement : dict
            Comparison metrics including:
            - name : str
                Annotator name
            - K : float
                Agreement score
            - VEO : float
                Vector embedding overlap
            - GED : float
                Graph edit distance
            - pageRank : float
                PageRank similarity
            - LO : float
                Learning outcome score
            - PN : float
                Prerequisite network score
        - can_be_refined : bool
            Whether video supports refinement
    """
    print("***** EKEEL - Video Annotation: main.py::burst_launch() ******")
    data = request.json

    video_id = data["id"]
    concepts = data["concepts"]
    concept_vocabulary = data["conceptVocabulary"]
    syn_burst = data["syn_burst"]
    burst_type = data["burst_type"]    
    
    # select burst type
    if syn_burst:
        print("Starting Burst " + burst_type + " with synonyms")
        concept_map,definitions = burst_extraction_with_synonyms(video_id, concepts, concept_vocabulary)
    else:
        print("Starting Burst " + burst_type)
        concept_map,definitions = burst_extraction(video_id,concepts)
    if burst_type == "semi":
        user = current_user.complete_name.replace(" ","_")+"_Burst_Analysis"
        name = current_user.complete_name
        email = current_user.email
    else:
        user = "Burst_Analysis"
        name = user
        email = user
    burst_graph = mongo.get_graph(user,video_id)

    # saving burst_graph on db if not already present
    if burst_graph is None:
        print("Saving Burst Graph on DB...")
        _,burst_graph = create_burst_graph(video_id,definitions,concept_map)
        local_vocabulary = create_local_vocabulary(video_id,concept_vocabulary)
        skos_concepts = local_vocabulary["skos:member"]
        downloadable_jsonld_graph = {"@context":burst_graph["@context"],"@graph":burst_graph["@graph"].copy()+[local_vocabulary]}
        burst_graph["@graph"].extend([{"id":concept["id"],"type":concept["type"]} for concept in skos_concepts])
        mongo.insert_graph({ "video_id":video_id,
                                "annotator_id":user,
                                "annotator_name":name,
                                "email":email,
                                "graph": burst_graph,
                                "conceptVocabulary": {"@context": burst_graph["@context"], 
                                                      "@graph": skos_concepts}})
    else:
        graph = sorted(burst_graph["@graph"],key=lambda x: int(x["id"][3:]) if str(x["id"][3:]).isnumeric() else 1042)
        for i,node in reversed(list(enumerate(graph))):
            if not str(node["id"]).startswith("concept_"):
                break
            else:
                graph.pop(i)
        downloadable_jsonld_graph = {"@context":burst_graph["@context"],"@graph":graph+[create_local_vocabulary(video_id,concept_vocabulary)]}

    data_summary = compute_data_summary(video_id,concept_map,definitions)
    
    # checks whether video has been segmented and if it is classifies ad slide video or not in order to enable refinement
    video = VideoAnalyzer("https://www.youtube.com/watch?v="+video_id,{"video_data"})
    can_be_refined = video.is_slide_video() and "slide_titles" in video.data["video_data"].keys()
        
    json = {
        "concepts": concepts,
        "concept_map": concept_map,
        "definitions": definitions,
        "data_summary": data_summary,
        "downloadable_jsonld_graph": downloadable_jsonld_graph,
        "agreement": None,
        "can_be_refined": can_be_refined
    }

    graphs = mongo.get_graphs_info(video_id)
    if graphs is not None:
        #first_annotator = graphs["annotators"][0]['id']
        #concept_map_annotator = db_mongo.get_concept_map(first_annotator, video_id)

        annotators = graphs["annotators"]
        # [NOTE] used me as annotator instead of annotators[0] for testing keywords
        my_id = current_user.mongodb_id
        indx_annotator = 0
        for i,annot in enumerate(annotators):
            if annot['id']==my_id:
                indx_annotator = i
                break
        indx_annotator = 0
        annotator = graphs["annotators"][indx_annotator]['id']
        concept_map_annotator = mongo.get_concept_map(annotator, video_id)

        veo, pageRank, LO, PN, ged_sim = calculate_metrics(concept_map, concept_map_annotator, concepts)

        json["agreement"] = {
            "name":graphs["annotators"][indx_annotator]["name"].replace("_"," "),
            "K": compute_agreement(concept_map, concept_map_annotator)["agreement"],
            "VEO": veo,
            "GED": ged_sim,
            "pageRank": round(pageRank, 3),
            "LO": round(LO, 3),
            "PN": round(PN, 3)
        }
    
    return json

@app.route('/refinement', methods=["GET", "POST"])
def video_segmentation_refinement():
    """
    Refine video segmentation and update concept definitions.

    This endpoint processes video segments to refine concept definitions
    and timestamps, storing updated annotations in the database.

    Parameters
    ----------
    data : dict 
        JSON request data containing:
        - id : str
            Video identifier
        - conceptVocabulary : dict
            Mapping of concepts to synonyms
        - definitions : dict
            Current concept definitions with timestamps
        - concept_map : dict
            Current concept relationships

    Returns
    -------
    dict
        JSON response containing:
        - definitions : dict
            Updated concept definitions with refined timestamps
        - downloadable_jsonld_graph : dict
            JSON-LD formatted graph containing:
            - @context : dict
                JSON-LD context definitions
            - @graph : list
                Updated nodes including:
                - Concept definitions
                - Relationships
                - SKOS vocabulary
    """
    data = request.json
    video_id = data["id"]
    concept_vocabulary = data["conceptVocabulary"]

    # for design this should not return None
    video = VideoAnalyzer(video_id, {"language"})
    new_concepts,definitions = video.adjust_or_insert_definitions_and_indepth_times(data["definitions"],_show_output=True)
    
    #from pprint import pprint
    #pprint(definitions)
    _,burst_graph = create_burst_graph(video_id,definitions,data["concept_map"])
    try:
        local_vocabulary = create_local_vocabulary(video_id,concept_vocabulary)
    except Exception as e:
        print(e)
        flash(e,'message')
    skos_concepts = local_vocabulary["skos:member"]
    if len(new_concepts) > 0:
        skos_concepts.extend(convert_to_skos_concepts(new_concepts,concept_vocabulary,video.data["language"]))
    downloadable_jsonld_graph = {"@context":burst_graph["@context"],"@graph":burst_graph["@graph"].copy()+[local_vocabulary]}
    burst_graph["@graph"].extend([{"id":concept["id"],"type":concept["type"]} for concept in skos_concepts])

    mongo.insert_graph({ "video_id":video_id,
                            "annotator_id":current_user.complete_name.replace(" ","_")+"_Burst_Analysis",
                            "annotator_name":"Burst_Analysis",
                            "email":"Burst_Analysis",
                            "graph": burst_graph,
                            "conceptVocabulary": {"@context": burst_graph["@context"], "@graph": skos_concepts}})

    return {"definitions":definitions,
            "downloadable_jsonld_graph":downloadable_jsonld_graph}
    
@app.route('/lemmatize_term', methods=["GET", "POST"])
def lemmatize_term():
    """
    Lemmatize a term in the specified language.

    This endpoint processes a concept term to extract its semantic structure
    and returns the lemmatized form along with linguistic information.

    Parameters
    ----------
    language : str
        Language code for lemmatization
    concept : str
        Term to be lemmatized

    Returns
    -------
    dict
        JSON response containing:
        - text : str
            Original input text
        - lemma : str
            Lemmatized form of the text
        - pos : str
            Part of speech tag
        - dep : str
            Dependency relation
        - head : str
            Head word in dependency relation
    """
    language = request.json["lang"]
    concept = request.json["concept"]
    return SemanticText(concept,language).get_semantic_structure_info()
    

DEBUG = False

def _open_application_in_browser(address):
    from webbrowser import open as open_page
    open_page('http://'+address+':5000/', new=1)

#workers_queue_scheduler(video_segmentations_queue)

if __name__ == '__main__':
    print("***** EKEEL - Video Annotation: main.py::__main__ ******")
    
    address = '127.0.0.1'
    #_open_application_in_browser(address)    
    app.run(host=address, threaded=True, debug=DEBUG) # port=5050\