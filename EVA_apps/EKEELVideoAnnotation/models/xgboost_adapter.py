"""
This module provides an adapter for the XGBoost pretrained model used for lecture type detection and text recognition.

Classes
-------
XGBoostModelAdapter
    Model adapter for the XGBoost pretrained model `xgboost500.sav` that classifies the lesson kind from images.

"""
from pickle import load as load_model
from media.image import ImageClassifier
from numpy import prod, empty, argmax, ndarray, zeros
from mediapipe.framework.formats.detection_pb2 import Detection
from xgboost import XGBClassifier

class XGBoostModelAdapter:
    '''
    Model adapter for the XGBoost pretrained model from the
    misc/lecture type detection and text recognition folder.

    Attributes
    ----------
    _labels : dict
        A dictionary mapping label indices to their corresponding names.

    Methods
    -------
    __init__(model_path: str) -> None
        Initializes the model adapter with the given model path.
    _extract_faces_info(detections: 'list[Detection] | None')
        Extracts face information from the current image.
    _extract_features_from_image(image: ImageClassifier, norm_minmax: bool = False)
        Extracts features from the given image.
    predict_probability(image: ImageClassifier)
        Predicts the probability distribution over classes for the given image.
    predict_max_confidence(image: ImageClassifier)
        Predicts the class with the highest confidence for the given image.
    get_label(prediction)
        Gets the label corresponding to the given prediction.
    is_enough_slidish_like(image: ImageClassifier)
        Predicts if the image is likely to be a slide with a small margin of confidence.
    '''

    _labels = {0: "Blackboard", 1: "Slide", 2: "Slide-and-Talk", 3: "Talk"}

    def __init__(self, model_path: str) -> None:
        '''
        Initializes the model adapter with the given model path.

        Parameters
        ----------
        model_path : str
            The path to the pretrained XGBoost model.
        '''
        try:
            self._model: XGBClassifier = load_model(open(model_path, 'rb'))
        except:
            raise FileExistsError("cannot find XGBoost model")

    def _extract_faces_info(self, detections: 'list[Detection] | None'):
        '''
        Extracts face information from the current image.

        Parameters
        ----------
        detections : list[Detection] or None
            A list of face detections or None if no faces are detected.

        Returns
        -------
        out_arr : ndarray
            An array with face information: [x_center, face_size, n_faces].
        '''
        out_arr = zeros((1, 3), dtype=float)
        if detections is None:
            return out_arr
        for detection in detections:
            bounding_box = detection.bounding_box
            xmin, width, height = bounding_box.origin_x, bounding_box.width, bounding_box.height
            face_size = width * height
            out_arr[0, 1] = max(out_arr[0, 1], face_size)
            if out_arr[0, 1] == face_size:
                out_arr[0, 0] = xmin + width / 2
            if out_arr[0, 2] < 2:
                out_arr[0, 2] += 1
        return out_arr

    def _extract_features_from_image(self, image: ImageClassifier, norm_minmax: bool = False):
        '''
        Extracts features from the given image.

        Parameters
        ----------
        image : ImageClassifier
            The image classifier object.
        norm_minmax : bool, optional
            Whether to normalize the features using min-max normalization (default is False).

        Returns
        -------
        out_arr : ndarray
            An array with extracted features.
        '''
        assert isinstance(image, ImageClassifier) and image.get_img().shape[2] == 3
        out_arr = empty((1, 19), dtype=float)
        out_arr[0, :16] = image.get_hists(normalize=norm_minmax, bins=16, grayscaled=True)
        if not norm_minmax:
            out_arr[0, :16] /= prod(image.get_img_shape()[:2])
        out_arr[0, 16:] = self._extract_faces_info(image.detect_faces())
        return out_arr

    def predict_probability(self, image: ImageClassifier):
        '''
        Predicts the probability distribution over classes for the given image.

        Parameters
        ----------
        image : ImageClassifier
            The image classifier object.

        Returns
        -------
        probs : ndarray
            The probability distribution over classes.
        '''
        return self._model.predict_proba(self._extract_features_from_image(image))

    def predict_max_confidence(self, image: ImageClassifier):
        '''
        Predicts the class with the highest confidence for the given image.

        Parameters
        ----------
        image : ImageClassifier
            The image classifier object.

        Returns
        -------
        prediction : int
            The class index with the highest confidence.
        '''
        return int(argmax(self.predict_probability(self._extract_features_from_image(image))))

    def get_label(self, prediction):
        '''
        Gets the label corresponding to the given prediction.

        Parameters
        ----------
        prediction : int or ndarray
            The prediction index or probability distribution.

        Returns
        -------
        label : str or dict
            The label corresponding to the prediction index or a dictionary of labels with their probabilities.
        '''
        if isinstance(prediction, int):
            assert 0 <= prediction <= 3
            return self._labels[prediction]
        elif isinstance(prediction, ndarray):
            assert prediction.shape == (1, 4)
            return {self._labels[i]: prediction[0, i] for i in range(4)}
        else:
            return None

    def is_enough_slidish_like(self, image: ImageClassifier):
        '''
        Predicts if the image is likely to be a slide with a small margin of confidence.

        Parameters
        ----------
        image : ImageClassifier
            The image classifier object.

        Returns
        -------
        is_slidish : bool
            True if the image is likely to be a slide, False otherwise.
        '''
        probs = self.predict_probability(image)
        best_slidish_prob = max(probs[0, (1, 2)])
        best_not_slidish_prob = max(probs[0, (0, 3)])
        return 1.15 * best_slidish_prob >= best_not_slidish_prob
