import vapoursynth as vs
from vapoursynth import core

'''
call using:

from ReplaceBlackFrames import ReplaceBlackFrames
rbf = ReplaceBlackFrames(clip, debug=True, thresh=0.1, method='previous')
clip = rbf.out

debug: whether to display the average luma
method: 
 'previous': replace black frames with the last non-black frame
 'interpolateSVP': replace black frames whit interpolatied frames using SVP (GPU)
 'interpolateSVPCPU': replace black frames whit interpolatied frames using SVP (CPU)
 'interpolateRIFE': replace black frames whit interpolatied frames using RIFE (https://github.com/styler00dollar/VapourSynth-RIFE-ncnn-Vulkan)

rifeSC: scene change threshld when RIFE is use for interpolation

When SVP is used input need to be YUV420P8.
When RIFE is used input need to be RGBS.
 
v0.0.3 added RIFE interpolation
v0.0.4 RIFE RGBH
'''
class ReplaceBlackFrames:
  # constructor
  def __init__(self, clip: vs.VideoNode, thresh: float=0.1, debug: bool=False, method: str='previous', rifeSC: float=0.15):
      self.thresh = thresh
      self.debug = debug
      self.method = method
      self.smooth = None
      self.rifeSC = rifeSC
      if thresh <= 0.001 or thresh >= 1:
        raise ValueError(f'ReplaceBlackFrames: "tresh" needs to fullfill: 0.001 < tresh < 1')  
      if rifeSC <0 or rifeSC > 1:
        raise ValueError(f'ReplaceBlackFrames: "float" needs to fullfill: 0 <= rifeSC <= 1')  
      if (method == 'interpolateSVP' or method == 'interpolateCPU') and (clip.format.id != vs.YUV420P8):
        raise ValueError(f'ReplaceBlackFrames: "clip" color format need to be YUV420P8 when SVP is used!\n{clip.format}')
      if (method == 'interpolateRIFE') and clip.format.id != vs.RGBS:
        raise ValueError(f'ReplaceBlackFrames: "clip" color format need to be RGBS when RIFE is used!\n{clip.format}')
      if (method == 'interpolateRIFE') and rifeSC != 0:
        self.clip = core.misc.SCDetect(clip=clip,threshold=rifeSC)
      self.clip = core.std.PlaneStats(clip)

  def previous(self, n, f):
    out = self.get_current_or_previous(n)
    if self.debug:
      return out.text.Text(text="Org, avg: "+str(f.props['PlaneStatsAverage']),alignment=8)            
    return out
  
  def interpolate(self, n, f):
    out = self.get_current_or_interpolate(n)
    if self.debug:
      return out.text.Text(text="avg: "+str(f.props['PlaneStatsAverage']),alignment=8)            
    return out

  def get_current_or_previous(self, n):
    for i in reversed(range(n+1)):
      if self.is_not_black(i):
        return self.clip[i]
    else:
      #all previous are black, return current n frame
      return self.clip[n]

  def interpolateWithRIFE(self, clip, n, start, end, rifeModel=22, rifeTTA=False, rifeUHD=False, rifeThresh=0):
    
    num = end - start
    self.smooth = core.rife.RIFE(clip, model=rifeModel, factor_num=num, tta=rifeTTA,uhd=rifeUHD)
    self.smooth_start = start
    self.smooth_end   = end
    return self.smooth[n-start]
    
    if clip.format != vs.RGBS:
      r = core.resize.Bicubic(r, format=clip.format, matrix_s=clip.get_frame(0).props['_Matrix'])

    r = core.std.Trim(r, first=1, last=1) 
    r = core.std.AssumeFPS(r, fpsnum=1, fpsden=1)
    a = core.std.Trim(clip1, first=0, last=firstframe-1) 
    b = core.std.Trim(clip1, first=firstframe+1)
    join = a + r + b
    return core.std.AssumeFPS(join, src=clip)

  def interpolateWithSVP(self, clip, n, start, end):   
      if self.method == 'interpolateSVP':
        super = core.svp1.Super(clip,"{gpu:1}")
      else: # self.method == 'interpolateSVPCPU':
        super = core.svp1.Super(clip,"{gpu:0}")
      vectors = core.svp1.Analyse(super["clip"],super["data"],clip,"{}")
      num = end - start
      self.smooth = core.svp2.SmoothFps(clip,super["clip"],super["data"],vectors["clip"],vectors["data"],f"{{rate:{{num:{num},den:1,abs:true}}}}")
      self.smooth_start = start
      self.smooth_end   = end
      return self.smooth[n-start]
      
  def get_current_or_interpolate(self, n):
    if self.is_not_black(n):
      #current non black selected
      return self.clip[n]

    #black frame, frame is interpolated
    for start in reversed(range(n+1)):
      if self.is_not_black(start):
        break
    else: #there are all black frames preceding n, return current n frame // will be executed then for-look does not end with a break
      return self.clip[n]
  
    for end in range(n, len(self.clip)):
      if self.is_not_black(end):
        break
    else:
      #there are all black frames to the end, return current n frame
      return self.clip[n]

    #does interpolated smooth clip exist for requested n frame? Use n frame from it.
    if self.smooth is not None and start >= self.smooth_start and end <= self.smooth_end:
      return self.smooth[n-start]

    #interpolating two frame clip  into end-start+1 fps
    if self.method == 'interpolateSVP' or self.method == 'interpolateCPU':
      clip = self.clip[start] + self.clip[end]
      clip = clip.std.AssumeFPS(fpsnum=1, fpsden=1)
      return self.interpolateWithSVP(clip, n, start, end)
    if self.method == 'interpolateRIFE':
      clip = self.clip[start] + self.clip[end]
      clip = clip.std.AssumeFPS(fpsnum=1, fpsden=1)
      return self.interpolateWithRIFE(clip, n, start, end, rifeThresh=self.rifeSC)
    else:
      raise ValueError(f'ReplaceBlackFrames: "method" \'{self.method}\' is not supported atm.')


  def is_not_black(self, n):
    return self.clip.get_frame(n).props['PlaneStatsAverage'] > self.thresh
  
  @property
  def out(self):
    if self.method == 'previous':
      return core.std.FrameEval(self.clip, self.previous, prop_src=self.clip)
    return core.std.FrameEval(self.clip, self.interpolate, prop_src=self.clip)