"""
Video processing module.

This module provides classes for handling video files, managing playback speed,
and extracting frames for analysis.

Classes
-------
LocalVideo
    Basic video file handler with frame extraction capabilities
SimpleVideo
    Basic video player with simple frame controls
VideoSpeedManager
    Advanced video processor with adaptive frame skipping
"""

#import ffmpeg
#ffmpeg.set_executable("/usr/bin/ffmpeg")
#from moviepy.editor import VideoFileClip
import os
import cv2
from numpy import clip,reshape,divmod,array,round

from math import floor, ceil, log2
from inspect import getfile
from typing import Tuple

from media.image import ImageClassifier,COLOR_BGR,COLOR_RGB,COLOR_GRAY
from pathlib import Path

VIDEOS_PATH = Path(__file__).parent.parent.joinpath("static","videos")


class LocalVideo:
    """
    Local video file handler with frame extraction capabilities.

    Attributes
    ----------
    _vidcap : cv2.VideoCapture
        OpenCV video capture object
    _output_colors : int
        Color scheme for output frames
    _num_colors : int
        Number of color channels
    _frame_size : tuple
        Forced frame size (width, height)
    _vid_id : str
        Video identifier

    Methods
    -------
    extract_next_frame()
        Extract next frame from video
    get_count_frames()
        Get total number of frames
    get_dim_frame()
        Get frame dimensions
    get_fps()
        Get frames per second
    get_id_vid()
        Get video identifier
    get_time_from_num_frame(num_frame, decimals)
        Convert frame number to time in seconds
    get_num_frame_from_time(seconds)
        Convert time to frame number
    set_num_frame(num_frame)
        Set current frame number
    set_frame_size(value)
        Set frame dimensions
    close()
        Release video capture resources
    """
    def __init__(self,video_id:str,output_colors:int=COLOR_BGR,forced_frame_size:'tuple[int,int] | None'= None,_testing_path=None):
        """
        Initialize video file handler.

        Parameters
        ----------
        video_id : str
            Identifier for the video file
        output_colors : int, optional
            Color scheme for output frames
        forced_frame_size : tuple or None, optional
            Force specific frame dimensions (width, height)
        _testing_path : str, optional
            Override path for testing
        """
        if output_colors!=COLOR_BGR and output_colors!=COLOR_RGB and output_colors!=COLOR_GRAY:
            raise Exception(f"Wrong parameter ouput_color value must be a COLOR_ value present in image.py")
        else:
            self._output_colors = output_colors
            if output_colors == COLOR_GRAY:
                self._num_colors = 1
            else:
                self._num_colors = 3
        self._frame_size = forced_frame_size
        self._vid_id = video_id
        if _testing_path is None:
            video_file_folder = VIDEOS_PATH.joinpath(video_id)
        else:
            video_file_folder = _testing_path
        self._vidcap = cv2.VideoCapture(os.path.join(video_file_folder,video_id+'.mp4'))
        #self._vidcap = cv2.VideoCapture(os.path.join(class_path, "static", "videos", video_id,f"{video_id}.mkv"))
        if not self._vidcap.isOpened():
            raise Exception(f"Can't find video: {video_id}")
    
    def __exit__(self, exc_type, exc_value, traceback):
        self._vidcap.relase()

    def close(self):
        """
        Release video capture resources.
        """
        self._vidcap.release()

    def extract_next_frame(self):
        """
        Extract next frame from video.

        Returns
        -------
        ndarray or None
            Image array if frame exists, None otherwise
        """
        has_frame, image = self._vidcap.read()
        if not has_frame:
            return None
        if self._frame_size is not None:
            image = cv2.resize(image,self._frame_size,interpolation=cv2.INTER_AREA)
        if self._output_colors != COLOR_BGR:
            image = cv2.cvtColor(image, self._output_colors)
        return reshape(image,(image.shape[0],image.shape[1],self._num_colors))
    
    def get_count_frames(self) -> int:
        """
        Get total number of frames in video.

        Returns
        -------
        int
            Total frame count
        """
        return int(self._vidcap.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_dim_frame(self):
        """
        Get frame dimensions.

        Returns
        -------
        tuple
            (width, height, num_colors)
        """
        if self._frame_size is not None:
            return (*self._frame_size,self._num_colors)
        
        return  int(self._vidcap.get(cv2.CAP_PROP_FRAME_WIDTH)), \
                int(self._vidcap.get(cv2.CAP_PROP_FRAME_HEIGHT)), \
                self._num_colors

    def get_fps(self) -> int:
        """
        Get video frames per second.

        Returns
        -------
        int
            Frames per second
        """
        return int(self._vidcap.get(cv2.CAP_PROP_FPS))

    def get_id_vid(self) -> str:
        """
        Get video identifier.

        Returns
        -------
        str
            Video ID
        """
        return self._vid_id

    def get_time_from_num_frame(self,num_frame:int,decimals:int=1):       #fr / (fr / s) = s
        """
        Convert frame number to time in seconds.

        Parameters
        ----------
        num_frame : int
            Frame number
        decimals : int, optional
            Number of decimal places

        Returns
        -------
        float
            Time in seconds
        """
        return round(num_frame/self.get_fps(), decimals=decimals)

    def get_num_frame_from_time(self,seconds:float):
        """
        Convert time to frame number.

        Parameters
        ----------
        seconds : float
            Time in seconds

        Returns
        -------
        int
            Frame number
        """
        return int(seconds*self.get_fps())
    
    def set_num_frame(self,num_frame:int):
        """
        Set current frame number.

        Parameters
        ----------
        num_frame : int
            Frame number to set
        """
        self._vidcap.set(cv2.CAP_PROP_POS_FRAMES,num_frame)
    
    def set_frame_size(self,value:'tuple[int,int]'):
        """
        Set frame dimensions.

        Parameters
        ----------
        value : tuple
            New frame dimensions (width, height)
        """
        self._frame_size = value

class VideoSpeedManager:
    """
    Advanced video processor with adaptive frame skipping.

    This class implements an adaptation of TCP fast retransmit algorithm
    for smart frame sampling.\n
    The principle is the following: ![TCP](https://encyclopedia.pub/media/common/202107/blobid20-60f5467ae42de.jpeg) \n
    With exponential growth of the frame skip rate, the algorithm tries to skip many identical frames until a threshold where the growth becomes linear.\n
    When a collision is detected (the text is changed with respect to the cached one), it rolls back to the first frame of that text occurrence and sets a linear growth of the frame skip rate.
    If no text is detected, the speed of skip will be exponential again.\n
    
    Attributes
    ----------
    vid_ref : LocalVideo
        Reference to video file handler
    _color_scheme : int
        Color scheme for output frames
    _curr_num_frame : int
        Current frame number
    _is_video_ended : bool
        Flag indicating video end
    _is_forced_speed : bool
        Flag for forced speed mode

    Methods
    -------
    get_frame()
        Get next frame based on current speed
    collide_and_get_fixed_num_frame()
        Handle text detection collision
    lock_speed(num_frames_skipped)
        Lock frame skip rate
    """
    def __init__(self,
                 video_id:str, 
                 output_colors:int=COLOR_BGR, 
                 max_dim_frame:Tuple[int,int]=(640,360),
                 time_decimals_accuracy:int=1,
                 exp_base:float=1.4,
                 lin_factor:float=2,
                 max_seconds_exp_window:float=5,
                 ratio_lin_exp_window_size:float=1.5,
                 _testing_path:str=None):
        self._init_params = (video_id,output_colors,max_dim_frame,time_decimals_accuracy,exp_base,lin_factor,max_seconds_exp_window,ratio_lin_exp_window_size)
        vid_ref = LocalVideo(video_id=video_id,output_colors=output_colors,_testing_path=_testing_path)
        frame_dim = vid_ref.get_dim_frame()[:2]
        max_scale_factor = max(divmod(frame_dim,max_dim_frame)[0])
        if max_scale_factor > 1: vid_ref.set_frame_size(tuple((array(frame_dim)/max_scale_factor).astype(int)))
        
        max_size_exp_window_frames = int(vid_ref.get_fps()*max_seconds_exp_window)
        max_size_lin_window_frames = int(max_size_exp_window_frames*ratio_lin_exp_window_size)
        start_sample_rate = ceil(clip(vid_ref.get_fps()*(10**(-time_decimals_accuracy)),1,vid_ref.get_fps()))

        self.vid_ref = vid_ref
        self._color_scheme = output_colors
        self._curr_num_frame = -start_sample_rate
        self._curr_x = 0
        self._frames = None
        self._curr_start_end_frames = None
        self._min_window_frame_size = start_sample_rate
        self._max_size_exp_window_frames = max_size_exp_window_frames
        self._max_size_lin_window_frames = max_size_lin_window_frames
        self._exp_base = exp_base
        self._y0_exp = start_sample_rate
        self._m = lin_factor
        self._y0_lin = max_size_exp_window_frames-lin_factor*(log2(max_size_lin_window_frames)/log2(exp_base))
        self._is_cong_avoid = False
        self._is_collided = False
        self._is_video_ended = False
        self._is_forced_speed = False
    
    def _exp_step(self,value:int): # (base^x - 1) + y0
        """
        Calculate exponential step size.

        Parameters
        ----------
        value : int
            Current step value

        Returns
        -------
        float
            Exponential step size
        """
        return (self._exp_base**value-1) + self._y0_exp
    
    def _lin_step(self,value:int):
        """
        Calculate linear step size.

        Parameters
        ----------
        value : int
            Current step value

        Returns
        -------
        float
            Linear step size
        """
        return self._m*value + self._y0_lin

    def is_video_ended(self):
        return self._is_video_ended

    def close(self):
        self.vid_ref.close()

    def get_video(self):
        """
        Get reference to video handler.

        Returns
        -------
        LocalVideo
            Reference to video handler object
        """
        return self.vid_ref

    def get_curr_num_frame(self):
        return self._curr_num_frame
    
    def get_prev_num_frame(self):
        return self._curr_num_frame - self._curr_window_frame_size

    def get_frame_from_num(self,num_frame:int):
        """
        Get specific frame by number.

        Parameters
        ----------
        num_frame : int
            Frame number to retrieve

        Returns
        -------
        ndarray
            Requested video frame
        """
        prev_num_frame = self._curr_num_frame
        self.vid_ref.set_num_frame(num_frame)
        frame = self.vid_ref.extract_next_frame()
        self.vid_ref.set_num_frame(prev_num_frame)
        return frame

    def get_percentage_progression(self) -> int:
        """
        Calculate video processing progress.

        Returns
        -------
        int
            Percentage of video processed (0-100)
        """
        if self._frames is not None:
            if len(self._frames) > 0:
                return ceil(self._curr_num_frame/self._frames[0][1] * 100)
            else:
                assert self._curr_start_end_frames is not None
                return ceil(self._curr_num_frame/self._curr_start_end_frames[1] * 100)
        return ceil(self._curr_num_frame/self.vid_ref.get_count_frames()*100)

    def is_full_video(self,frames):
        return len(frames)==1 and frames[0][0]==0 and frames[0][1]==self.vid_ref.get_count_frames()-1

    def _debug_get_speed(self):
        if self._curr_window_frame_size is not None:
            return self._curr_window_frame_size
        return 0

    def _get_num_last_frame(self,vid_ref: LocalVideo):
        curr_start_end_frames = self._curr_start_end_frames
        if curr_start_end_frames is not None:
            return curr_start_end_frames[1] - 1
        else:
            return vid_ref.get_count_frames() - 1

    def _get_frame_from_internal_frames(self):
        curr_num_frame = self._curr_num_frame
        curr_start_end_frames = self._curr_start_end_frames
        if curr_start_end_frames is None or curr_num_frame + self._curr_window_frame_size >= curr_start_end_frames[1]:
            try:
                assert self._frames is not None
                self._curr_start_end_frames = self._frames.pop()
                return self._curr_start_end_frames[0]
            except IndexError:
                self._frames = []
                return self.vid_ref.get_count_frames()
            
        return self._curr_num_frame

    def get_frame(self):
        """
        Get next frame based on current speed settings.

        The frame skip rate adapts based on current phase:
        - Collision: minimum skip rate
        - Exponential: exponentially increasing skip
        - Linear: linearly increasing skip
        - Forced: fixed skip rate

        Returns
        -------
        ndarray
            Next video frame
        """
        if self._is_forced_speed:
            next_size_window_frame = self._curr_window_frame_size 
        else:
            if self._is_collided:
                next_size_window_frame = self._min_window_frame_size
            else:
                if self._is_cong_avoid:
                    # linear step
                    next_size_window_frame = clip(  self._lin_step(self._curr_x),
                                                    self._min_window_frame_size,
                                                    self._max_size_lin_window_frames )
                else:
                    # exponential step
                    next_size_window_frame = clip(  self._exp_step(self._curr_x),
                                                    self._min_window_frame_size,
                                                    self._max_size_exp_window_frames )
                    if next_size_window_frame == self._max_size_exp_window_frames:
                        self._is_cong_avoid = True
                self._curr_x += 1
               
        self._curr_window_frame_size = int(next_size_window_frame)
        
        if self._frames is not None:
            self._curr_num_frame = self._get_frame_from_internal_frames()
        
        vid_ref = self.vid_ref
        self._curr_num_frame += self._curr_window_frame_size 
        vid_ref.set_num_frame(self._curr_num_frame)
        frame = vid_ref.extract_next_frame()
        if frame is None:
            self._is_video_ended = True
            num_last_frame = self._get_num_last_frame(vid_ref)
            vid_ref.set_num_frame(num_last_frame)
            frame = vid_ref.extract_next_frame()
            self._curr_num_frame = num_last_frame + 1 
        return frame

    def _bin_search(self, min_offset:int, max_offset:int, step_size:int):
        L = min_offset
        R = max_offset
        vid_ref = self.vid_ref
        frame = ImageClassifier().set_color_scheme(vid_ref._output_colors)
        while L <= R:
            m = floor((L+R)/2)
            vid_ref.set_num_frame(m)
            if frame.set_img(vid_ref.extract_next_frame()).extract_text():
                R = m - 1
            else:
                L = m + 1
        else:
            m = ceil((L+R)/2)
        return m + m%step_size # align to the step_size

    def collide_and_get_fixed_num_frame(self):
        """
        Handle text detection collision by finding first frame with text.

        Uses binary search to find the first frame where text appears
        between current position and last known position.

        Returns
        -------
        int
            Frame number where text first appears
        """
        curr_num_frame = self._curr_num_frame
        max_rollback_frame = int(clip(curr_num_frame - self._curr_window_frame_size, 0, curr_num_frame))
        if self._curr_start_end_frames is not None:
            max_rollback_frame = int(clip(max_rollback_frame, self._curr_start_end_frames[0], max_rollback_frame + self._curr_window_frame_size))
        self._curr_num_frame = self._bin_search(    max_rollback_frame,
                                                    curr_num_frame,
                                                    self._min_window_frame_size )
        self._is_collided = True
        return self._curr_num_frame

    def end_collision(self):
        """
        Reset collision state and prepare for linear growth phase.

        Sets internal flags to transition from collision handling
        to linear growth phase.
        """
        self._is_collided = False
        self._is_cong_avoid = True
        self._curr_x = 0
        self._y0_lin = self._min_window_frame_size

    def rewind_to(self,num_frame:int):
        """
        Rewind video to specific frame.

        Parameters
        ----------
        num_frame : int
            Target frame number
        """
        if not self._is_forced_speed:
            if self._is_collided:
                prev_size_window_frame = self._min_window_frame_size
            elif self._is_cong_avoid:
                prev_size_window_frame = clip(  self._lin_step(self._curr_x-1),
                                                self._min_window_frame_size,
                                                self._max_size_exp_window_frames )
            else:
                prev_size_window_frame = clip(  self._exp_step(self._curr_x-1),
                                                self._min_window_frame_size,
                                                self._max_size_exp_window_frames )
        else:
            prev_size_window_frame = self._curr_window_frame_size
        self._curr_num_frame = num_frame - int(prev_size_window_frame)

    def reset(self):
        self.__init__(*self._init_params)

    def lock_speed(self,num_frames_skipped:'int | None'= None):
        """
        Lock frame skip rate to fixed value.

        Parameters
        ----------
        num_frames_skipped : int or None, optional
            Number of frames to skip, uses minimum if None
        """
        self._is_forced_speed = True
        if num_frames_skipped is None:
            self._curr_window_frame_size = self._min_window_frame_size
        else:
            self._curr_window_frame_size = num_frames_skipped
            if self._curr_num_frame < 0:
                self._curr_num_frame = -num_frames_skipped
    
    def _get_frame_offset(self,offset:int):
        """
        Returns the i+offset frame with respect to the one set inside the structure
        """
        prev_speed = self._curr_window_frame_size
        was_forced = self._is_forced_speed
        self._is_forced_speed = True
        self._curr_window_frame_size = offset
        frame = self.get_frame()
        self._curr_window_frame_size = prev_speed
        self._is_forced_speed = was_forced
        return frame

    def get_following_frame(self):
        """
        Get next sequential frame.

        Returns
        -------
        ndarray
            Next frame in sequence
        """
        if self._is_video_ended or self._curr_num_frame + self._min_window_frame_size > self.get_video().get_count_frames()-1:
            self._curr_num_frame -= (self._min_window_frame_size+1)
        return self._get_frame_offset(self._min_window_frame_size)

    def set_analysis_frames(self,frames:'list[tuple[int,int]]'):
        """
        Set specific frame ranges for analysis.

        Parameters
        ----------
        frames : list of tuple
            List of (start_frame, end_frame) ranges
        """
        self._frames = sorted(frames,reverse=True)
       
class SimpleVideo:
    """
    Basic video player with simple frame controls.

    Attributes
    ----------
    video : cv2.VideoCapture
        OpenCV video capture object
    _curr_step : int
        Current frame step size
    _curr_frame_idx : int
        Current frame index

    Methods
    -------
    close()
        Release video resources
    get_count_frames()
        Get total number of frames
    get_fps()
        Get frames per second
    get_frame()
        Get next frame based on step size
    roll(offset)
        Move frame position by offset
    rewind()
        Return to start of video
    set_step(step)
        Set frame step size
    get_frame_index(one_step_back)
        Get current frame index
    """
    def __init__(self, video_id: str):
        """
        Initialize simple video player.

        Parameters
        ----------
        video_id : str
            Identifier for the video file
        """
        self.video = cv2.VideoCapture(Path(__file__).parent.joinpath("static","videos",video_id,video_id+".mp4").__str__())
        if not self.video.isOpened():
            raise Exception("Error loading video in SimpleVideo")
        self._curr_step = 1
        self._curr_frame_idx = 0
        
    def close(self):
        """
        Release video capture resources.
        """
        self.video.release()

    def get_count_frames(self) -> int:
        """
        Get total number of frames in video.

        Returns
        -------
        int
            Total frame count
        """
        return int(self.video.get(cv2.CAP_PROP_FRAME_COUNT))
    
    def get_fps(self) -> int:
        """
        Get video frames per second.

        Returns
        -------
        int
            Frames per second
        """
        return int(self.video.get(cv2.CAP_PROP_FPS))

    def get_frame(self):
        """
        Get next frame based on current step size.

        Returns
        -------
        ndarray
            Next video frame
        """
        self._curr_frame_idx += self._curr_step
        self.video.set(cv2.CAP_PROP_POS_FRAMES,self._curr_frame_idx)
        return self.video.read()[1]
    
    def roll(self, offset: int):
        """
        Move frame position by given offset.

        Parameters
        ----------
        offset : int
            Number of frames to move (positive or negative)
        """
        self._curr_frame_idx += offset
        self.video.set(cv2.CAP_PROP_POS_FRAMES,self._curr_frame_idx)
    
    def rewind(self):
        """
        Return to first frame of video.
        """
        self.roll( - self._curr_frame_idx )
        
    def set_step(self, step):
        """
        Set frame step size.

        Parameters
        ----------
        step : int
            Number of frames to skip between each get_frame call
        """
        self._curr_step = step
        
    def get_frame_index(self, one_step_back: bool = False):
        """
        Get current frame index.

        Parameters
        ----------
        one_step_back : bool, optional
            If True, returns index minus one step

        Returns
        -------
        int
            Current frame index
        """
        return self._curr_frame_idx - one_step_back * self._curr_step
    

if __name__ == '__main__':
    vid_id = "ujutUfgebdo" # slide video
    #vid_id = "YI3tsmFsrOg" # not slide video
    #vid_id = "UuzKYffpxug" # slide + person video
    #vid_id = "g8w-IKUFoSU" # forensic arch
    #vid_id = 'GdPVu6vn034'
    #download('https://youtu.be/ujutUfgebdo')
    #print(download('https://www.youtube.com/watch?v='+vid_id))
    print(download_video("https://www.youtube.com/watch?v=jKF2QLmZi1Q"))
    VideoSpeedManager("D4PGqxGWCT0")
    
    #color_scheme_for_analysis = ColorScheme.BGR
    #   BGR: is the most natural for Opencv video reader, so we avoid some matrix transformations
    #   RGB: should be used for debug visualization
    #   GRAY: can perform faster but less precise and may require more strict threshold 
    #         EDIT: grayscale don't work with face recognition so it's better not to use it 
    #extract_text_from_video(vid_id,color_scheme_for_analysis)
    #video.close()
    # https://www.youtube.com/watch?v=ujutUfgebdo
    #download("https://www.youtube.com/watch?v=UuzKYffpxug&list=PLV8Xi2CnRCUm0QOaRfPuMzFNUVxmYlEiV&index=5")