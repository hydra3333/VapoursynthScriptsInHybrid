import vapoursynth as vs
core = vs.core

def fillWithMVTools(clip):
  super = core.mv.Super(clip, pel=2)
  vfe = core.mv.Analyse(super, truemotion=True, isb=False, delta=1)
  vbe = core.mv.Analyse(super, truemotion=True, isb=True, delta=1)
  return core.mv.FlowInter(clip, super, mvbw=vbe, mvfw=vfe, time=50)
    
def fillWithRIFE(clip, firstframe=None, rifeModel=22, rifeTTA=False, rifeUHD=False, sceneThresh=0.15):
  clip1 = core.std.AssumeFPS(clip, fpsnum=1, fpsden=1)
  start = core.std.Trim(clip1, first=firstframe-1, length=1)
  end = core.std.Trim(clip1, first=firstframe+1, length=1)
  startend = start + end
  startend = core.resize.Bicubic(startend, format=vs.RGBS, matrix_in_s="709")
  r = core.rife.RIFE(startend, model=rifeModel, tta=rifeTTA, uhd=rifeUHD, sc=sceneThresh>0)
  r = core.resize.Bicubic(r, format=clip.format, matrix_s="709")
  r = core.std.Trim(r, first=1, last=1)
  r = core.std.AssumeFPS(r, fpsnum=1, fpsden=1)
  a = core.std.Trim(clip1, first=0, last=firstframe-1)
  b = core.std.Trim(clip1, first=firstframe+1)
  join = a + r + b
  return core.std.AssumeFPS(join, src=clip)

def fillWithSVP(clip, firstframe=None, gpu=False):
  clip1 = core.std.AssumeFPS(clip, fpsnum=1, fpsden=1)
  start = core.std.Trim(clip1, first=firstframe-1, length=1)
  end = core.std.Trim(clip1, first=firstframe+1, length=1)
  startend = start + end
  
  if gpu:
    super  = core.svp1.Super(startend,"{gpu:1}")
  else:
    super  = core.svp1.Super(startend,"{gpu:0}")
  vectors= core.svp1.Analyse(super["clip"],super["data"],startend,"{}")
  r = core.svp2.SmoothFps(startend,super["clip"],super["data"],vectors["clip"],vectors["data"],"{}")
  
  r = core.std.Trim(r, first=1, last=1) 
  r = core.std.AssumeFPS(r, fpsnum=1, fpsden=1)
  a = core.std.Trim(clip1, first=0, last=firstframe-1) 
  b = core.std.Trim(clip1, first=firstframe+1)
  join = a + r + b
  return core.std.AssumeFPS(join, src=clip)


def fillWithGMFSSUnion(clip, firstframe=None, gmfssModel=0, sceneThresh=0.15):
  from vsgmfss_fortuna import gmfss_fortuna
  clip1 = core.std.AssumeFPS(clip, fpsnum=1, fpsden=1)
  start = core.std.Trim(clip1, first=firstframe-1, length=1)
  end = core.std.Trim(clip1, first=firstframe+1, length=1)
  startend = start + end
  r = core.resize.Bicubic(startend, format=vs.RGBH, matrix_in_s="709")
  r = gmfss_fortuna(r, model=gmfssModel, sc_threshold=sceneThresh)
  r = core.resize.Bicubic(r, format=clip.format, matrix_s="709")
  r = core.std.Trim(r, first=1, last=1) 
  r = core.std.AssumeFPS(r, fpsnum=1, fpsden=1)
  a = core.std.Trim(clip1, first=0, last=firstframe-1) 
  b = core.std.Trim(clip1, first=firstframe+1)
  join = a + r + b
  return core.std.AssumeFPS(join, src=clip)



def fillWithSVP(clip, firstframe=None, gpu=False):
  clip1 = core.std.AssumeFPS(clip, fpsnum=1, fpsden=1)
  start = core.std.Trim(clip1, first=firstframe-1, length=1)
  end = core.std.Trim(clip1, first=firstframe+1, length=1)
  startend = start + end
 
  if gpu:
    super  = core.svp1.Super(startend,"{gpu:1}")
  else:
    super  = core.svp1.Super(startend,"{gpu:0}")
  vectors= core.svp1.Analyse(super["clip"],super["data"],startend,"{}")
  r = core.svp2.SmoothFps(startend,super["clip"],super["data"],vectors["clip"],vectors["data"],"{}")
  
  r = core.std.Trim(r, first=1, last=1) 
  r = core.std.AssumeFPS(r, fpsnum=1, fpsden=1)
  a = core.std.Trim(clip1, first=0, last=firstframe-1) 
  b = core.std.Trim(clip1, first=firstframe+1)
  join = a + r + b
  return core.std.AssumeFPS(join, src=clip)
    
def FillSingleDrops(clip, thresh=0.3, method="mv", rifeModel=22, rifeTTA=False, rifeUHD=False, sceneThresh=0.15, gmfssModel=0, debug=False):
  core = vs.core
  if not isinstance(clip, vs.VideoNode):
    raise ValueError('This is not a clip')

  if clip.format.color_family != vs.YUV:
    raise ValueError('FillSingleDrops requires YUV input')
    
  if sceneThresh > 0 and (method == "rife" or method == "gmfssfortuna"):
    clip = core.misc.SCDetect(clip=clip,threshold=sceneThresh)
    
  def selectFunc(n, f):
    if f.props['PlaneStatsDiff'] > thresh or n == 0 or n >= clip.num_frames -1 :
      if debug:
        return core.text.Text(clip=clip,text="Org, diff: "+str(f.props['PlaneStatsDiff']),alignment=8)
      return clip
    else:
      if method == "mv":
        filldrops=fillWithMVTools(clip)
      elif method == "svp":
        filldrops=fillWithSVP(clip,n)
      elif method == "svp_gpu":
        filldrops=fillWithSVP(clip,n,gpu=True)
      elif method == "rife":
        filldrops = fillWithRIFE(clip,n,rifeModel,rifeTTA,rifeUHD, sceneThresh)
      elif method == "gmfssfortuna":
        filldrops = fillWithGMFSSUnion(clip,n,gmfssModel,sceneThresh)
      else:
        raise vs.Error('FillDrops: Unknown method '+method)   
    if debug:
       return core.text.Text(clip=filldrops,text=method+", diff: "+str(f.props['PlaneStatsDiff']),alignment=8)
    return filldrops
          
  diffclip = core.std.PlaneStats(clip, clip[0] + clip)
  fixed = core.std.FrameEval(clip, selectFunc, prop_src=diffclip)
  return fixed

def InsertSingle(clip, afterEveryX=2, method="mv", rifeModel=0, rifeTTA=False, rifeUHD=False, sceneThresh=0.15, gmfssModel=0, debug=False):
  core = vs.core
  if not isinstance(clip, vs.VideoNode):
    raise ValueError('This is not a clip')
    
  if clip.format.color_family != vs.YUV:
    raise ValueError('InsertSingle requires YUV input')  
  
  if sceneThresh > 0 and (method == "rife" or method == "gmfssfortuna"):
    clip = core.misc.SCDetect(clip=clip,threshold=sceneThresh)
       
  def selectFunc(n):
    if n == 0 or n%afterEveryX != 0:
      return clip
    else:
      
      if method == "mv":
        insertFrame=fillWithMVTools(clip)
      elif method == "svp":
        insertFrame=fillWithSVP(clip,n)
      elif method == "svp_gpu":
        insertFrame=fillWithSVP(clip,n,gpu=True)
      elif method == "rife":
        insertFrame = fillWithRIFE(clip,n,rifeModel,rifeTTA,rifeUHD,sceneThresh)
      elif method == "gmfssfortuna":
        insertFrame = fillWithGMFSSUnion(clip,n,gmfssModel,sceneThresh)
      else:
        raise vs.Error('InsertSingle: Unknown method '+method)   
    return insertFrame.text.Text("Interpolated")

  return core.std.FrameEval(clip, selectFunc)
  
  
def ReplaceSingle(clip, frameList, method="mv", rifeModel=0, rifeTTA=False, rifeUHD=False, sceneThresh=0.15, gmfssModel=0, debug=False):
    core = vs.core
    if not isinstance(clip, vs.VideoNode):
        raise ValueError('This is not a clip')
    if clip.format.color_family != vs.YUV:
       raise ValueError('ReplaceSingle requires YUV input')
    if sceneThresh != 0 and (method == "rife" or method == "gmfssfortuna"):
       clip = core.misc.SCDetect(clip=clip, threshold=sceneThresh)

    def selectFunc(n):
      if n in frameList:
        if method == "mv":
            insertFrame = fillWithMVTools(clip)
        elif method == "svp":
            insertFrame = fillWithSVP(clip, n)
        elif method == "svp_gpu":
            insertFrame = fillWithSVP(clip, n, gpu=True)
        elif method == "rife":
            insertFrame = fillWithRIFE(clip, n, rifeModel, rifeTTA, rifeUHD, sceneThresh)
        elif method == "gmfssfortuna":
            insertFrame = fillWithGMFSSUnion(clip, n, gmfssModel, sceneThresh)
        else:
            raise vs.Error('replaceSingle: Unknown method ' + method)
        if debug:
           return core.text.Text(clip=insertFrame,text=method+", replaced frame: "+str(n),alignment=8)
        return insertFrame;
      if debug:
        return core.text.Text(clip=clip,text="kept frame: "+str(n),alignment=8)
      return clip
    return core.std.FrameEval(clip, selectFunc)