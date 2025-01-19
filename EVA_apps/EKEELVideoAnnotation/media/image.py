"""
Image processing module for video analysis.

This module provides functionality for image processing, text extraction,
face detection, and image comparison operations.

Classes
-------
FaceDetectorSingleton
    Singleton class for face detection using MediaPipe
ImageClassifier
    Main class for image analysis and text extraction

Functions
---------
draw_bounding_boxes_on_image
    Draws bounding boxes on an image
draw_bounding_boxes_on_image_classifier
    Draws bounding boxes on an ImageClassifier instance
show_image
    Display an image using matplotlib
"""

import cv2
import pytesseract
pytesseract.pytesseract.tesseract_cmd = "/usr/bin/tesseract"
import os
from pathlib import Path
import mediapipe as mp
from mediapipe import Image, ImageFormat
from numpy import round, dot, diag, reshape, zeros, uint8, array, inf, mean, var, transpose, all, empty, abs,ones
from numpy.linalg import norm
from typing import List, Tuple
from bisect import insort_left
import numpy as np


MODEL_PATH = Path(__file__).parent.parent.joinpath("models","blaze_face_detector_short_range.tflite")

if not os.path.exists(MODEL_PATH):
    import requests
    response = requests.get("https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/latest/blaze_face_short_range.tflite")
    with open(MODEL_PATH, 'wb') as file:
        file.write(response.content)

class FaceDetectorSingleton(object):
    """
    Singleton class for MediaPipe face detection.

    Attributes
    ----------
    _instance : FaceDetectorSingleton
        Single instance of the detector
    _detector : MediaPipe.FaceDetector
        MediaPipe face detector instance

    Methods
    -------
    detect(image)
        Detect faces in the given image
    """
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(FaceDetectorSingleton, cls).__new__(cls)
            options = mp.tasks.vision.FaceDetectorOptions(base_options=mp.tasks.BaseOptions(model_asset_path=MODEL_PATH))
            cls._detector = mp.tasks.vision.FaceDetector.create_from_options(options)
        return cls._instance

    def detect(self, image):
        return self._detector.detect(Image(image_format=ImageFormat.SRGB, data=image))

COLOR_BGR:int=0
COLOR_GRAY = cv2.COLOR_BGR2GRAY
COLOR_RGB = cv2.COLOR_BGR2RGB

# Distance measurements - Cosine Similairity or Mean Absolute Distance
#DIST_MEAS_METHOD_COSINE_SIM:int=0
#DIST_MEAS_METHOD_MEAN_ABSOLUTE_DIST:int=1

class ImageClassifier:
    """
    Image analysis and classification wrapper.

    Attributes
    ----------
    _face_detector : FaceDetectorSingleton
        Face detector instance
    _texts_with_contour : list
        Detected text regions with bounding boxes
    _image : ndarray
        Original image data
    _image_grayscaled : ndarray
        Grayscale version of image

    Methods
    -------
    copy()
        Create a copy of the classifier
    detect_faces()
        Detect faces in the image
    extract_text(return_text=False, with_contours=False)
        Extract text from image
    is_same_image(other, threshold=3)
        Compare with another image
    has_changed_slide(other)
        Check if slide has changed
    """
    _face_detector = FaceDetectorSingleton()
    _texts_with_contour:'list[tuple[str,tuple[int,int,int,int]]] | None' = None
    _image = None
    _image_grayscaled = None
    
    def __init__(self,image) -> None:
        """
        Initialize image classifier.

        Parameters
        ----------
        image : ndarray
            Input image to analyze
        """
        self._init_params_ = (image) 
        self._image = image
        
    def copy(self):
        """
        Create a deep copy of the classifier.

        Returns
        -------
        ImageClassifier
            New classifier instance with copied data
        """
        new_img:ImageClassifier = ImageClassifier(self._image)
        new_img._image_grayscaled = self._image_grayscaled
        new_img._texts_with_contour = self._texts_with_contour
        return new_img

    def detect_faces(self):
        """
        Detect faces in the image.

        Returns
        -------
        list
            List of MediaPipe face detection results

        Raises
        ------
        Exception
            If no image is loaded
        """
        if self._image is None:
            raise Exception("No Image to detect")
        return self._face_detector.detect(self._image).detections


    def _convert_grayscale(self, new_axis=False):
        """
        Convert image to grayscale.

        Parameters
        ----------
        new_axis : bool, optional
            Add channel dimension if True

        Returns
        -------
        ndarray
            Grayscale image
        """
        self._image_grayscaled = cv2.cvtColor(self._image,cv2.COLOR_BGR2GRAY)
        if new_axis:
            self._image_grayscaled = self._image_grayscaled[:,:,None]
        return self._image_grayscaled

    def _preprocess_image(self,img_bw):
        """
        Preprocess image for text detection.

        Parameters
        ----------
        img_bw : ndarray
            Binary image to process

        Returns
        -------
        list
            List of detected contours
        """
        img_bw.flags.writeable = True
        img_bw = img_bw.copy()
        cv2.threshold(img_bw, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV,img_bw)
        cv2.dilate(img_bw, cv2.getStructuringElement(cv2.MORPH_RECT, (6, 6)), img_bw,iterations = 3)
        return cv2.findContours(img_bw, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)[0]
    
    def _read_text_with_bbs(self, img, xywh_orig, conf=0) -> List[Tuple[str,Tuple[int,int,int,int]]]:
        '''
        Read of text is made in this way:
            - scan with pytesseract every word of the image (which is passed as cropped) and return as dict of words and other infos
            - for every word in the structure i: check if is regognized with a confidence above conf, then save the delta line with respect to the previous
            
            - if there's a delta line equal to zero i check if the previous line is ended ( -> there's a new sentence)
            - otherwise we are in the middle of a sentence so width of the sentence must be accumulated (accounting also for spaces)
            - the heights and start Y of every sentence are calculated as the average of every word (sometimes there's noise or other elemens like mouse cursors)
            
            - if instead there's a delta line > 0 the sentence element is formed. 
            - New line is appended and bounding boxes are normalized with respect to the original size of the full image
            - lastly if there's still some text in the structure but the iterator has ended, save it
        '''
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
        texts = data['text']
        xs = data['left']
        ys = data['top']
        ws = data['width']
        hs = data['height']
        confs = data['conf']
        lines = data['line_num']
        texts_with_bb = []
        x_off,y_off,img_w,img_h = xywh_orig

        last_text_indx = len(texts)-1
        text = ''
        ended_line = True
        for i, word in enumerate(texts):
            next_line = lines[i+1] if i < last_text_indx else lines[i]-1 
            if confs[i]>=conf:
                # there won't be line change
                if next_line-lines[i]==0:
                    # first word of line: reset vars
                    if ended_line:
                        start_x = xs[i]
                        ys_words = []
                        hs_words = []
                        cumul_w = 0
                        ended_line = False
                    # middle sentence word: add width for previous space
                    else:
                        cumul_w += xs[i]-(xs[i-1]+ws[i-1])
                    text += word + ' '
                    ys_words.append(ys[i])
                    hs_words.append(hs[i])
                    cumul_w += ws[i]
                # there will be line change
                else:
                    # single word phrase: reset vars
                    if ended_line:
                        start_x = xs[i]
                        ys_words = [ys[i]]
                        hs_words = [hs[i]]; 
                        cumul_w = 0
                    # last word of sentence before new line: add width for previous space
                    else:
                        cumul_w += xs[i]-(xs[i-1]+ws[i-1])
                    text += word + '\n'
                    # if there's some text flush it
                    if text.strip(): 
                        texts_with_bb.append((text,((start_x+x_off)/img_w,
                                                    (mean(ys_words)+y_off)/img_h,
                                                    (cumul_w + ws[i])/img_w,
                                                    mean(hs_words)/img_h)))
                    text = ''
                    ended_line = True    
        else:
            # if there's still some text flush it
            if not ended_line:
                texts_with_bb.append((text,((start_x+x_off)/img_w,
                                            (mean(ys_words)+y_off)/img_h,
                                            (cumul_w + ws[i])/img_w,
                                            mean(hs_words)/img_h)))

        return texts_with_bb

    def _scan_image_for_text_and_bounding_boxes(self):
        '''
        Image is preprocessed and cropped in multiple rectangles of texts, then these are singularly analyzed\n
        Firstly turns into black and white\,
        _preprocess_image() finds the contours of text\n
        for each contour a tuple of (text, bounding_boxes(x,y,w,h)) is read and insorted based on it's min Y value of the contours 
        
        Prerequisite
        ------------
        RGB, BGR but with len(image_shape) == 3 always\n
        '''
        img_bw = self._convert_grayscale()
        img_height,img_width = img_bw.shape
        contours = self._preprocess_image(img_bw)
        y_and_texts_with_bb = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            img_cropped = img_bw[y:y+h,x:x+w]
            text_read = self._read_text_with_bbs(img_cropped,(x,y,img_width,img_height))
            if text_read:
                insort_left(y_and_texts_with_bb,(y,text_read))
        self._texts_with_contour = [text_with_bb 
                                    for (_,texts_with_bb) in y_and_texts_with_bb
                                    for text_with_bb in texts_with_bb]
        

    def extract_text(self,return_text=False,with_contours=False):
        """
        Extract text from image.

        Parameters
        ----------
        return_text : bool, optional
            Return extracted text if True
        with_contours : bool, optional
            Include bounding box coordinates if True

        Returns
        -------
        bool or str or list
            Depends on parameters:
            - bool: if text found (default)
            - str: extracted text if return_text=True
            - list: text and contours if both True
        """
        if self._image is None:
            self._texts_with_contour = [[]]
        self._scan_image_for_text_and_bounding_boxes()
        if return_text and with_contours:
            return self._texts_with_contour
        elif return_text and not with_contours:
            return ''.join([elem[0] for elem in self._texts_with_contour])
        return bool(self._texts_with_contour)

    def get_detected_text(self,with_contours=True):
        """
        Get previously detected text.

        Parameters
        ----------
        with_contours : bool, optional
            Include bounding box coordinates

        Returns
        -------
        list or str
            Text with contours or just text
        """
        assert self._texts_with_contour is not None
        if with_contours: return self._texts_with_contour
        else: return ''.join([elem[0] for elem in self._texts_with_contour])

    def get_img_shape(self):
        assert self._image is not None
        return self._image.shape

    def is_same_image(self,other:'ImageClassifier', threshold=3) -> bool:
        """
        Compare two images using MSE.

        Parameters
        ----------
        other : ImageClassifier
            Image to compare against
        threshold : int, optional
            MSE threshold for similarity

        Returns
        -------
        bool
            True if images are similar
        """
        return np.mean((self._image - other._image)**2) < threshold

        comp_method = self._comp_method
        if comp_method == DIST_MEAS_METHOD_COSINE_SIM:
            return all(self.get_cosine_similarity(other_image) >= self._similarity_threshold)
        elif comp_method == DIST_MEAS_METHOD_MEAN_ABSOLUTE_DIST:
            return all(self.get_mean_distance(other_image) <= self._similarity_threshold)
        else:
            return False
        
    def has_changed_slide(self, other:"ImageClassifier") -> bool:
        """
        Detect significant changes between images.

        Parameters
        ----------
        other : ImageClassifier
            Image to compare against

        Returns
        -------
        bool
            True if significant changes detected
        """
        if self._image_grayscaled is None:
            self._convert_grayscale()
        if other._image_grayscaled is None:
            other._convert_grayscale()

        # Compute the absolute difference between the current frame and the previous frame
        frame_diff = cv2.absdiff(self._image_grayscaled, other._image_grayscaled)

        # Threshold the difference to get the regions with significant changes
        _, thresh = cv2.threshold(frame_diff, 20, 255, cv2.THRESH_BINARY)

        # Find contours in the thresholded image
        return bool(len([cv2.boundingRect(contour) 
                         for contour in cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0] 
                         if cv2.contourArea(contour) > img1_g.shape[0]*img2_g.shape[1]/20]))
    
    def has_image(self):
        return self._image is not None



    def get_cosine_similarity(self,other:'ImageClassifier',on_histograms=True,rounding_decimals:int= 10):
        """
        Calculate cosine similarity between images.

        Parameters
        ----------
        other : ImageClassifier
            Image to compare against
        on_histograms : bool, optional
            Use histogram comparison if True
        rounding_decimals : int, optional
            Decimal precision for result

        Returns
        -------
        ndarray
            Similarity scores per color channel
        """
        assert self._image is not None and other._image is not None and self._image.shape == other._image.shape
        
        if on_histograms:   # looks like it's faster
            this_mat = self.get_hists(normalize=True)
            other_mat = other.get_hists(normalize=True)
        else:   # reshape to num_colors flatten rows, one for each color channel and normalize
            this_image = self._image
            other_image = other._image
            this_mat = reshape(this_image,(this_image.shape[2],this_image.shape[0]*this_image.shape[1])).astype(float)
            other_mat = reshape(other_image,(other_image.shape[2],other_image.shape[0]*other_image.shape[1])).astype(float)
            cv2.normalize(this_mat,this_mat,0,1,cv2.NORM_MINMAX)
            cv2.normalize(other_mat,other_mat,0,1,cv2.NORM_MINMAX)
        cosine_sim = round( diag(dot(this_mat,other_mat.T))/(norm(this_mat,axis=1)*norm(other_mat,axis=1)), 
                            decimals=rounding_decimals)
        return cosine_sim

    def get_mean_distance(self,other:'ImageClassifier',on_histograms=True):
        assert self._image is not None and other._image is not None
        if on_histograms:
            this_mat = self.get_hists(normalize=True)
            other_mat = other.get_hists(normalize=True)
            dists = abs(this_mat - other_mat)
            return mean(dists,axis=1)
        else:
            this_mat = self._image.astype(int)
            other_mat = other._image
            dists = abs(this_mat - other_mat)
            return mean(reshape(dists,(dists.shape[0]*dists.shape[1],dists.shape[2])),axis=0)

    def _get_grayscaled_img(self):
        '''
        Converts to grayscale
        '''
        if self._color_scheme == COLOR_BGR:
            return cv2.cvtColor(self._image, cv2.COLOR_BGR2GRAY)
        elif self._color_scheme == COLOR_RGB:
            return cv2.cvtColor(self._image, cv2.COLOR_RGB2GRAY)
        else:
            return self._image

    def get_hists(self,normalize:bool=False,bins:int=256,grayscaled=False):
        """
        Generate image histograms.

        Parameters
        ----------
        normalize : bool, optional
            Normalize histogram values
        bins : int, optional
            Number of histogram bins
        grayscaled : bool, optional
            Convert to grayscale first

        Returns
        -------
        ndarray
            Image histograms per channel
        """
        assert self._image is not None
        # CV2 calcHist is fast but can't calculate 3 channels at once 
        # so the fastest way is making a list of arrays and merging with cv2 merge
        if grayscaled:
            img = self._convert_grayscale(new_axis=True)
        else:
            img = self._image
        img = cv2.split(img)
        num_channels = len(img)
        hists = []
        for col_chan in range(num_channels):
            hist = cv2.calcHist(img,channels=[col_chan],mask=None,histSize=[bins],ranges=[0,256])
            if normalize:
                cv2.normalize(hist,hist,0,1,cv2.NORM_MINMAX)
            hists.append(hist)
        hists = cv2.merge(hists)
        if len(hists.shape) > 2: hists = transpose(hists,(2,0,1))
        return reshape(hists,(num_channels,bins))
    
    def get_img(self, text_bounding_boxes=False):
        if not text_bounding_boxes or not self._texts_with_contour:
            return self._image
        return draw_bounding_boxes_on_image(self._image,[elem[1] for elem in self._texts_with_contour])

    def set_img(self,img):
        """
        Set new image for analysis.

        Parameters
        ----------
        img : ndarray
            New image to analyze

        Returns
        -------
        ImageClassifier
            Self for method chaining
        """
        self._image = img
        self._image_grayscaled = None
        self._texts_with_contour = None
        return self

    def set_color_scheme(self,color_scheme:int):
        """
        Set color scheme for image processing.

        Parameters
        ----------
        color_scheme : int
            One of COLOR_BGR, COLOR_RGB, COLOR_GRAY

        Returns
        -------
        ImageClassifier
            Self for method chaining

        Raises
        ------
        AssertionError
            If invalid color scheme
        """
        assert color_scheme == COLOR_BGR or color_scheme == COLOR_RGB or color_scheme == COLOR_GRAY 
        self._color_scheme = color_scheme
        return self
    
    def _debug_show_image(self,axis=None):
        if self._image is not None:
            if self._color_scheme == COLOR_BGR:
                image = self._image.copy()
                image = cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
            else:
                image = self._image
            if axis is not None:
                axis.axis('off')
                axis.imshow(image)
            else:
                from matplotlib import pyplot as plt
                plt.axis('off')
                plt.imshow(image)


def draw_bounding_boxes_on_image(img, bounding_boxes:'list[tuple[(int,int,int,int)]]'):
    """
    Draw bounding boxes on an image.

    Parameters
    ----------
    img : ndarray
        Input image
    bounding_boxes : list
        List of (x,y,w,h) bounding box coordinates

    Returns
    -------
    ndarray
        Image with drawn bounding boxes
    """
    img = img.copy()
    if len(img.shape) == 3:
        img_h,img_w,_ = img.shape
    else:
        img_h,img_w = img.shape
    for xywh in bounding_boxes:
        # rescale bbs
        x = int(xywh[0]*img_w); y = int(xywh[1]*img_h); w = int(xywh[2]*img_w); h = int(xywh[3]*img_h)
        # draw
        cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 1)
    return img

def draw_bounding_boxes_on_image_classifier(image:ImageClassifier):
    """
    Draw detected text bounding boxes on ImageClassifier.

    Parameters
    ----------
    image : ImageClassifier
        Input image classifier with detected text

    Returns
    -------
    ndarray
        Image with drawn bounding boxes
    """
    assert image.get_img() is not None and image.get_detected_text() is not None
    return draw_bounding_boxes_on_image(image.get_img(),[bbs for _,bbs in image.get_detected_text()])

def show_image(image,color_scheme=COLOR_BGR):
    """
    Display an image using matplotlib.

    Parameters
    ----------
    image : ndarray
        Input image to display
    color_scheme : int
        Color scheme of the input image
    """
    from matplotlib import pyplot as plt
    if color_scheme == COLOR_BGR:
        cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
    plt.axis('off')
    plt.imshow(image)
    plt.show()

if __name__ == '__main__':
    from PIL import Image
    from pathlib import Path

    img_tit1 = Image.open(Path(__file__).parent.joinpath("screenT1.png"))
    img_tit2 = Image.open(Path(__file__).parent.joinpath("screenT2.png"))
    
    img1 = Image.open(Path(__file__).parent.joinpath("screen1.png"))
    img2 = Image.open(Path(__file__).parent.joinpath("screen2.png"))

    #se = (np.array(img1) - np.array(img2)) ** 2
    #mse = np.mean(se)

    #se = (np.array(img_tit1) - np.array(img_tit2)) ** 2
    #mse2 = np.mean(se)
    image2 = np.array(img_tit2)

    # Convert the frame to grayscale
    img1_g = cv2.cvtColor(np.array(img_tit1), cv2.COLOR_BGR2GRAY)
    img2_g = cv2.cvtColor(np.array(img_tit2), cv2.COLOR_BGR2GRAY)
    
    # Compute the absolute difference between the current frame and the previous frame
    frame_diff = cv2.absdiff(img1_g, img2_g)
    
    # Threshold the difference to get the regions with significant changes
    _, thresh = cv2.threshold(frame_diff, 20, 255, cv2.THRESH_BINARY)
    
    # Find contours in the thresholded image
    contours = [cv2.boundingRect(contour) for contour in cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[0] if cv2.contourArea(contour) > img1_g.shape[0]*img2_g.shape[1]/20]
    
    # Draw bounding boxes around the contours
    for contour in contours:
        x, y, w, h = contour
        cv2.rectangle(image2, (x, y), (x + w, y + h), (0, 255, 0), 2)
    
    #import os
    #img = cv2.cvtColor(cv2.imread(os.path.join(os.path.dirname(os.path.abspath(__file__)),"svm_dataset","screen01.png")), cv2.COLOR_BGR2RGB)
    #classif = ImageClassifier(image_and_scheme=[img,COLOR_RGB])
    #print(classif.detect_faces())
    #text = classif.extract_text(return_text=True)
    #print(f"text: {text}")