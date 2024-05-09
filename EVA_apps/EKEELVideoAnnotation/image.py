import cv2
import pytesseract
import os
import mediapipe as mp
from mediapipe.framework.formats.detection_pb2 import Detection
from numpy import round, dot, diag, reshape, zeros, uint8, array, inf, mean, var, transpose, all, empty, abs,ones
from numpy.linalg import norm
from typing import List, Tuple
from bisect import insort_left

mp_face_detection = mp.solutions.face_detection
mp_drawing = mp.solutions.drawing_utils

COLOR_BGR:int=0
COLOR_GRAY = cv2.COLOR_BGR2GRAY
COLOR_RGB = cv2.COLOR_BGR2RGB

DIST_MEAS_METHOD_COSINE_SIM:int=0
DIST_MEAS_METHOD_MEAN_ABSOLUTE_DIST:int=1

class ImageClassifier:
    """
    Wraps an image to find patterns in it

    ----------
    Parameters:
    ----------
        image_and_scheme : a tuple of the image in RGB - BGR - GRAYSCALE mode and the color_scheme

        image_shape : alternatively can set shape of a total black image
    """

    _texts_with_contour:'list[tuple[str,tuple[int,int,int,int]]] | None' = None
    _faces:'list[Detection] | None' = None
    _threshold: 'tuple[float,float,float] or float or None'
    _comp_method:int or None
    
    def __init__(self,comp_method:int or None=None,threshold:'tuple[float,float,float] or float or None'=None,image_and_scheme=None, image_shape=None) -> None:
        assert comp_method is None or comp_method == DIST_MEAS_METHOD_COSINE_SIM or comp_method == DIST_MEAS_METHOD_MEAN_ABSOLUTE_DIST
        self._init_params_ = (comp_method,threshold,image_and_scheme,image_shape) # for copy() to work correctly must be in the same positions
        self._comp_method = comp_method
        if image_shape is not None:
            self._image = zeros(image_shape, dtype=uint8)
            self._color_scheme = None
        elif image_and_scheme is not None:
            self._image = image_and_scheme[0]
            self._color_scheme = image_and_scheme[1]
        else:
            self._image = None
            self._color_scheme = None
        self._threshold = threshold
        
    def copy(self):
        '''
        makes a copy of itself and returns it
        '''
        new_img = ImageClassifier(*self._init_params_)
        if self._image is not None:
            new_img._image = self._image
        return new_img

    def detect_faces(self, model:int=1, min_conf=0.2, return_contours=False):
        '''
        Search and save faces internally
        
        Parameters
        -----------
        
        model : int 0 for short range detection (2 meters from camera), 1 for long range detection (> 5 meters)
        min_conf: minimum confidence for the recognition

        Returns
        -----------
        True if at least one face has been found and return_contours is False
        otherwise returns the full array of contours for every face
        '''
        assert isinstance(model,int) and 0 <= model <= 1 and 0 <= min_conf <= 1
        if self._image is not None:
            with mp_face_detection.FaceDetection(model_selection=model, min_detection_confidence=min_conf) as face_detection:
                self._image.flags.writeable = False
                if self._color_scheme == COLOR_BGR:
                    self._image = cv2.cvtColor(self._image, cv2.COLOR_BGR2RGB)
                    self._faces = face_detection.process(self._image)
                    self._image.flags.writeable = True
                    self._image = cv2.cvtColor(self._image, cv2.COLOR_RGB2BGR)
                else:
                    self._faces = face_detection.process(self._image)
                    self._image.flags.writeable = True
                if return_contours:
                    return self._faces.detections
                return bool(self._faces.detections)

    def _convert_grayscale(self,third_dimension:bool=False):
        '''
        Converts from RGB or BGR to GRAYSCALE with shape (img_height, img_width)
        '''
        img = self._image
        if self._color_scheme==COLOR_BGR:
            img_bw = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
        elif self._color_scheme==COLOR_RGB:
            img_bw = cv2.cvtColor(img,cv2.COLOR_RGB2GRAY)
        else:
            if third_dimension:
                img_bw = img
            else:
                img_bw = reshape(img,(img.shape[0],img.shape[1]))
        
        return img_bw

    def _preprocess_image(self,img_bw):
        '''
        Image is binarized and dilated to find contours of texts
        '''
        img_bw.flags.writeable = True
        img_bw = img_bw.copy()
        cv2.threshold(img_bw, 0, 255, cv2.THRESH_OTSU | cv2.THRESH_BINARY_INV,img_bw)
        cv2.dilate(img_bw, cv2.getStructuringElement(cv2.MORPH_RECT, (12, 12)), img_bw,iterations = 3)
        return cv2.findContours(img_bw, cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)[0]
    
    def _read_text_with_bbs(self, img, xywh_orig, conf=80) -> List[Tuple[str,Tuple[int,int,int,int]]]:
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
        Image is preprocessed and cropped in multiple rectangles of texts, then these are singularly analyzed
        
        Prerequisite
        ------------
        RGB, BGR but with len(image_shape) == 3 always\n
        DEPRECATED grayscale as image input of this function is deprecated because face recognition require 3 channels image
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
        '''
        Search and save text internally
        
        Returns
        -----------
        True if at least one text has been found and return_contours is False
        otherwise returns the full array of contours for every text
        '''
        assert self._image is not None and len(self._image.shape) == 3
        self._scan_image_for_text_and_bounding_boxes()
        if return_text and with_contours:
            return self._texts_with_contour
        elif return_text and not with_contours:
            return ''.join([elem[0] for elem in self._texts_with_contour])
        return bool(self._texts_with_contour)

    def draw_detected_faces(self):
        '''
        Draws detected faces on image and returns the image with contours
        '''
        assert self._faces is not None
        detections = self._faces
        image = self._image.copy()
        for detection in detections:
            mp_drawing.draw_detections(image, detection)
        return image

    def get_detected_text(self,with_contours=True):
        assert self._texts_with_contour is not None
        if with_contours: return self._texts_with_contour
        else: return ''.join([elem[0] for elem in self._texts_with_contour])
        

    def get_detected_faces(self,with_contours=False):
        assert self._faces is not None
        if with_contours:
            return self._faces
        else:
            return len(self._faces)

    def get_img_shape(self):
        assert self._image is not None
        return self._image.shape

    def is_similar_to(self,other_image:'ImageClassifier') -> bool:
        '''
        Compares two images in terms of comparison methods set at the initialization
        '''
        comp_method = self._comp_method
        if comp_method == DIST_MEAS_METHOD_COSINE_SIM:
            return all(self.get_cosine_similarity(other_image) >= self._threshold)
        elif comp_method == DIST_MEAS_METHOD_MEAN_ABSOLUTE_DIST:
            return all(self.get_mean_distance(other_image) <= self._threshold)
        else:
            return False


    def get_cosine_similarity(self,other:'ImageClassifier',on_histograms=True,rounding_decimals:int= 10):
        '''
        Compute cosine similarity between two images

        Params
        ------ 
        on_histograms : FASTER if True analysis is performed on histograms
        rounding_decimals : number of decimals of precision
        
        Returns
        --------
        1xN numpy array with N as the number of color channels (3 for RGB-BGR and 1 for GRAYSCALE)
        '''
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
        '''
        Generate image histogram\n
        
        Parameters
        ----------
        normalize : if true normalizes on minmax
        grayscaled : if true the image is processed to grayscale
        '''
        assert self._image is not None
        # CV2 calcHist is fast but can't calculate 3 channels at once 
        # so the fastest way is making a list of arrays and merging with cv2 merge
        if grayscaled:
            img = self._convert_grayscale(third_dimension=True)
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
        self._image = img
        self._texts_with_contour = None
        self._faces = None
        return self

    def set_color_scheme(self,color_scheme:int):
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
    '''
    given an image and bounding boxes obtained with detect text
    '''
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
    '''
    Draws on the image classifier text already extracted
    '''
    assert image.get_img() is not None and image.get_detected_text() is not None
    return draw_bounding_boxes_on_image(image.get_img(),[bbs for _,bbs in image.get_detected_text()])

def show_image(image,color_scheme=COLOR_BGR):
    from matplotlib import pyplot as plt
    if color_scheme == COLOR_BGR:
        cv2.cvtColor(image,cv2.COLOR_BGR2RGB)
    plt.axis('off')
    plt.imshow(image)
    plt.show()

if __name__ == '__main__':
    import os
    img = cv2.cvtColor(cv2.imread(os.path.join(os.path.dirname(os.path.abspath(__file__)),"svm_dataset","screen01.png")), cv2.COLOR_BGR2RGB)
    classif = ImageClassifier(image_and_scheme=[img,COLOR_RGB])
    print(classif.detect_faces())
    text = classif.extract_text(return_text=True)
    print(f"text: {text}")