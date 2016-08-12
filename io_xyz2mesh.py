# -*- coding: utf8 -*-
bl_info = {
    "name": "Import XYZ to Mesh",
    "author": "europrimus@free.fr",
    "version": (0, 6),
    "blender": (2, 7, 0),
    "location": "File > Import > Import XYZ to Mesh",
    "description": "Import text point file to new Mesh object",
    "warning": "",
    "wiki_url": "",
    "tracker_url": "",
    "category": "Import"}


import bpy
from mathutils import Vector
from math import sqrt
from bpy_extras.object_utils import AddObjectHelper, object_data_add
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty, FloatProperty, FloatVectorProperty
from bpy.types import Operator
from time import time


#GeoRef : gestion du géoréférencement
def GeoRef_get(context):
    print("-"*5,"GeoRef_get","-"*5)
    try:
      DeltaX=context.scene["Georef X"]
      DeltaY=context.scene["Georef Y"]
      DeltaZ=context.scene["Georef Z"]
      EPSG=context.scene["Georef EPSG"]
      ScaleXY=context.scene["Georef ScaleXY"]
      ScaleZ=context.scene["Georef ScaleZ"]
    except KeyError:
      return "NoGeoRef"
    return {"EPSG":EPSG,"ScaleXY":ScaleXY,"ScaleZ":ScaleZ,"DeltaX":DeltaX,"DeltaY":DeltaY,"DeltaZ":DeltaZ}


def GeoRef_set(context,EPSG,X,Y,Z,ScaleXY=1,ScaleZ=1):
    print("-"*5,"GeoRef_set","-"*5)
    r=10
    try:
      DeltaX=context.scene["Georef X"]
      DeltaY=context.scene["Georef Y"]
    except KeyError:
      DeltaX=round(X/r,0)*r
      context.scene["Georef X"]=DeltaX
      DeltaY=round(Y/r,0)*r
      context.scene["Georef Y"]=DeltaY
    else:
      context.scene["Georef Z"]=0

    try:
      DeltaZ=context.scene["Georef Z"]
    except KeyError:
      DeltaZ=round(Z/r,0)*r
      context.scene["Georef Z"]=DeltaZ

    try:
      EPSG=context.scene["Georef EPSG"]
    except KeyError:
      context.scene["Georef EPSG"]=EPSG
    try:
      ScaleXY=context.scene["Georef ScaleXY"]
    except KeyError:
      context.scene["Georef ScaleXY"]=ScaleXY
    try:
      ScaleZ=context.scene["Georef ScaleZ"]
    except KeyError:
      context.scene["Georef ScaleZ"]=ScaleZ
    
    return {"EPSG":EPSG,"ScaleXY":ScaleXY,"ScaleZ":ScaleZ,"DeltaX":DeltaX,"DeltaY":DeltaY,"DeltaZ":DeltaZ}



def read_line(File,Config):
  Line=File.readline()
  if Config["Debug"]:
    print("-"*3,"read_line","-"*3)
    print("Line:",Line)
  Line=Line.rstrip("\n")
  Temp=Line.split(Config["Sep"])
  if Config["Debug"]:print("Temp",Temp)
  try :
    X=round(float(Temp[Config["X"]]),Config["Round"])
    Y=round(float(Temp[Config["Y"]]),Config["Round"])
    Z=round(float(Temp[Config["Z"]]),Config["Round"])
    if Config["Debug"]:print("XYZ",X,Y,Z)
  except :
    print("Error: X Y or Z are not a number")
    return "ERROR"
  return [X,Y,Z]

def subtract(A,B):
  result=[]
  n=0
  for n in range(0,len(A)):
    result.append(A[n]-B[n])
    n=n+1
  return result


def read_PointFile(context,FileName,Config):
  print("-"*5,"read_PointFile","-"*5)
  if Config["Debug"]:print("Config:",Config)
  if Config["Debug"] : print("FileName:",FileName)
  GeoRef=GeoRef_get(context)
  if GeoRef == "NoGeoRef" :
    File=open(FileName, 'rt',errors='surrogateescape')
    coord=read_line(File,Config)
    File.close()
    print("coord:",coord)
#    GeoRef={"EPSG":Config["EPSG"],"ScaleXY":1,"ScaleZ":1,"DeltaX":coord[0],"DeltaY":coord[1],"DeltaZ":coord[2]}
#    GeoRef_set(context,GeoRef["EPSG"],GeoRef["DeltaX"],GeoRef["DeltaY"],GeoRef["DeltaZ"],GeoRef["ScaleXY"],GeoRef["ScaleZ"])
    GeoRef=GeoRef_set(context,Config["EPSG"],coord[0],coord[1],coord[2])
    
#  print("GeoRef:",GeoRef["EPSG"],GeoRef["ScaleXY"],GeoRef["ScaleZ"],GeoRef["DeltaX"],GeoRef["DeltaY"],GeoRef["DeltaZ"])
  if Config["EPSG"] != GeoRef["EPSG"]: 
    print("-"*3,"Warning: EPSG code different than the scene. File to be loaded:",Config["EPSG"],"scene:",GeoRef["EPSG"])
  if Config["Debug"]:print("GeoRef:",GeoRef)
  Delta=[GeoRef["DeltaX"],GeoRef["DeltaY"],GeoRef["DeltaZ"]]

  Config["Min"] = Vector((Config["Min"][0]-Delta[0], Config["Min"][1]-Delta[1],Config["Min"][2]-Delta[2]))
  Config["Max"] = Vector((Config["Max"][0]-Delta[0], Config["Max"][1]-Delta[1],Config["Max"][2]-Delta[2]))

  print ("-"*3,"Load_File","-"*3)
  Verts=[]			#Vecteurs des sommets
  Edges=[]			#Aretes
  Faces=[]
  NbPoints=0			#initialisation du nombre de point chargé
  NbEdges=0			#initialisation du d'arrétes créé
  NbLine=0
  OldPoint=Vector()
  NbPointsDisp=False


#lecture du fichier de points
  File=open(FileName, 'rt',errors='surrogateescape')
  coord=""
  while coord != "ERROR" and NbLine < Config["MaxLine"]:
    coord=read_line(File,Config)
    if coord =="ERROR" : break
    NbLine+=1
    if NbPoints % 10**3 ==0 and NbPointsDisp :
      print(NbPoints,"points loaded")
      NbPointsDisp=False
    if NbLine % Config["Decimate"] == 0:
      NewPoint=Vector(subtract(coord,Delta))
      if Config["Debug"]:print("NewPoint",NewPoint)
      if Config["Min"][0] <= NewPoint[0] <= Config["Max"][0] and Config["Min"][1] <= NewPoint[1] <= Config["Max"][1] and Config["Min"][2] <= NewPoint[2] <= Config["Max"][2]:
        if NewPoint==OldPoint:
          if Config["Debug"]:print("point déja chargé",NewPoint,"=",OldPoint)
        else:
          Verts.append(NewPoint)
          NbPoints+=1
          NbPointsDisp=True
          OldPoint=NewPoint
          if NbPoints >= Config["MaxPoints"]:
            if Config["Debug"]:print("Nombre de point dépassé",NbPoints,">",Config["MaxPoints"])
            break
      else:
        if Config["Debug"]:print("hors selection",Config["Min"]," <=",NewPoint," <= ",Config["Max"])

  File.close()
#Création des sommets
  #print("Verts",Verts)
  MeshName=FileName.split("/")[-1]
  print("MeshName",MeshName)
  Mesh = bpy.data.meshes.new(name=MeshName)
  Mesh.from_pydata(Verts, Edges, Faces)
  Mesh.validate(verbose=Config["Debug"])
  if Config["Debug"]: print("Mesh:",Mesh)
  bpy.context.scene.cursor_location = (0.0, 0.0, 0.0)
  Object=object_data_add(context, Mesh)

  return (NbPoints,NbLine)




class ImportPointFile(Operator, ImportHelper):
    """This appears in the tooltip of the operator and in the generated docs"""
    bl_idname = "import_test.point_file"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import XYZ to Mesh"
    bl_options = {'UNDO'}

    # ImportHelper mixin class uses this
    filename_ext = ".txt"
    filter_glob = StringProperty(name="Filtre", default="*.txt;*.xyz;*.csv", options={'HIDDEN'} )

    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.

    #use_setting = BoolProperty(name="Example Boolean",description="Example Tooltip",default=True,)

#Configuration
    Config_sep = StringProperty(name="separator",description="separator between column",default=" ",)
    Config_StartLine = FloatProperty(name="Start line",description="Start at line n",default=1,min=0,max=10,soft_min=0,soft_max=10,step=1, precision=0,subtype="NONE",unit="NONE")
    Config_MaxLine = FloatProperty(name="Max line",description="max of line to read",default=10**6,min=10,max=10**7,soft_min=10,soft_max=10**7,step=100, precision=0,subtype="NONE",unit="NONE")

    Config_X = FloatProperty(name="column X",description="X are in column n",default=1,min=0,max=10,soft_min=0,soft_max=10,step=1, precision=0,subtype="NONE",unit="NONE")
    Config_Y = FloatProperty(name="column Y",description="Y are in column n",default=2,min=0,max=10,soft_min=0,soft_max=10,step=1, precision=0,subtype="NONE",unit="NONE")
    Config_Z = FloatProperty(name="column Z",description="Z are in column n",default=3,min=0,max=10,soft_min=0,soft_max=10,step=1, precision=0,subtype="NONE",unit="NONE")

    Config_min=FloatVectorProperty(name="min", description="minimum bouding box corner", default=(0, 0, 0), step=10, precision=0, options={'ANIMATABLE'}, subtype='NONE', size=3, )
    Config_max=FloatVectorProperty(name="max", description="maximum bouding box corner", default=(10**7, 10**7, 1000), step=10, precision=0, options={'ANIMATABLE'}, subtype='NONE', size=3, )

    Config_maxpoints=FloatProperty(name="Max point",description="maximum points to be loaded",default=10**6,min=100,max=10**7,step=100, precision=0,subtype="NONE",unit="NONE")
    Config_round=FloatProperty(name="round",description="rounding at n",default=3,min=0,max=6,step=1, precision=0,subtype="NONE",unit="NONE")
    Config_decimate=FloatProperty(name="decimate",description="load 1 point each n",default=1,min=1,max=10**6,step=1, precision=0,subtype="NONE",unit="NONE")


#    Config_MaxDist = FloatProperty(name="Distance max",description="Distance maximal pour créer des edges (0: ne pas créer les edges",default=0,min=0,max=10,soft_min=0,soft_max=10,step=0.1, precision=3,subtype="NONE",unit="NONE")

    Config_EPSG = FloatProperty(name="EPSG code",description="Code EPSG (coordinate system)",default=3947,min=0,max=10000,soft_min=0,soft_max=10000,step=1, precision=0,subtype="NONE",unit="NONE")

    Config_debug= BoolProperty(name="Debug",description="see debuging info in systeme console",default=False,)

    def execute(self, context):
        debut=time()
        result = read_PointFile(context,self.filepath,{"Sep" : str(self.Config_sep), "StartLine" : int(self.Config_StartLine), "Debug" : self.Config_debug, "X" : int(self.Config_X)-1, "Y" : int(self.Config_Y)-1, "Z" : int(self.Config_Z)-1, "Min":self.Config_min, "Max":self.Config_max, "MaxPoints":int(self.Config_maxpoints), "Round":int(self.Config_round), "EPSG":self.Config_EPSG, "Decimate":self.Config_decimate, "MaxLine":self.Config_MaxLine})
        duree=round(time()-debut,3)
        print(result[1],"Lines read and",result[0],"points loaded in",duree,"s")
        if result[1] > 1:
          result={'FINISHED'}
        else:
          result={'ERROR'}
        return result


# Only needed if you want to add into a dynamic menu
def menu_func_import(self, context):
    self.layout.operator(ImportPointFile.bl_idname, text="Import XYZ to Mesh")


def register():
    bpy.utils.register_class(ImportPointFile)
    bpy.types.INFO_MT_file_import.append(menu_func_import)


def unregister():
    bpy.utils.unregister_class(ImportPointFile)
    bpy.types.INFO_MT_file_import.remove(menu_func_import)


if __name__ == "__main__":
    print("-"*10,"register","-"*10)
    register()

    # test call
    bpy.ops.import_test.point_file('INVOKE_DEFAULT')
    
    #unregister()
    #print("unregister")