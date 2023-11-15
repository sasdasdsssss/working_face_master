import vtkmodules.all as vtk
from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QCheckBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import open3d as o3d
import numpy as np
from PySide6.QtCore import Qt
import math
from Actors import *
from camera_controller import CameraController
from readers import *


class CustomQVTKRenderWindowInteractor(QVTKRenderWindowInteractor):
    # 目前支持的文件类型
    SUPPORTFILETYPE = {
        "STL": vtk.vtkSTLReader,  # 存放相应类的引用
        "ply": vtk.vtkPLYReader,  # 两种ply文件
        "pcd": Custom_vtkPCDReader,
        "vtk": vtk.vtkDataSetReader
    }
    FILEFILETER = "Text files (*.STL *.ply *.pcd *.vtk)"

    def __init__(self, window):
        super().__init__()
        self.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.window = window

        # 创建渲染器
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.1, 0.1, 0.1)
        self.GetRenderWindow().AddRenderer(self.renderer)
        # 创建当前渲染器摄像头控制器
        self.camera_controller = CameraController(
            self.renderer.GetActiveCamera())

        # 设置点云演员突出点时的基本属性
        self.base_property = vtk.vtkProperty()

        # 将基本属性的亮度和漫反射与滑条同步, /100.0是因为滑条范围为0-1000
        self.base_property.SetAmbient(self.window.horizontalSlider_ambient.value() / 100.0)
        self.base_property.SetDiffuse(self.window.horizontalSlider_diffuse.value() / 100.0)

        # 预加载水平面、网格线、环境图片-------------------------------------------
        # 1.实例一个水平平面演员
        self.plane_actorXY = HorizontalPlaneActor("XY")
        self.plane_actorYZ = HorizontalPlaneActor("YZ")
        self.plane_actorXZ = HorizontalPlaneActor("XZ")

        # 2.实例一个坐标轴演员
        # self.cube_axes = CubeAxesActor(self)
        self.cube_axes = vtk.vtkAxesActor()
        # 创建一个坐标轴变换小部件
        axes_transform_widget = vtk.vtkAxesTransformWidget()
        axes_transform_widget.SetInteractor(self)
        # self.cube_axes.SetCamera(self.camera_controller.camera)

        # 创建一个坐标轴演员的助手
        # axes_widget = vtk.vtkOrientationMarkerWidget()
        # axes_widget.SetOrientationMarker(self.cube_axes)
        # axes_widget.SetInteractor(self)
        # axes_widget.SetViewport(0.0, 0.0, 0.2, 0.2)  # 设置坐标轴显示的位置
        # axes_widget.SetEnabled(1)
        # axes_widget.InteractiveOn()

        # 3.创建背景环境
        self.sphere_actor = SphereActor()
        # self.renderer.AddActor(self.sphere_actor)  # 默认强制有环境图片，暂时不可选
        # --------------------------------------------------------------

        # 存储清空按钮时不会被清除的演员
        self.fixed_actors = [self.plane_actorXY, self.cube_axes]  # 暂时剔除 self.sphere_actor
        # 存储当前加载的点云演员
        self.point_cloud_actors = []
        self.point_cloud_actors_checkBoxs = []

        # 正在显示某信息则设置为True,此标志用来帮助释放资源
        self.show_planeXY = False
        self.show_planeYZ = False
        self.show_planeXZ = False
        self.show_axes = False
        self.highlight_point = False  # 是否突出点

        # 直接加载工作场景,并加载网格面xy
        # self.load_workspace()
        self.toggled_planeXY()
        self.load_label()

    def load_workspace(self):
        files_name = ['zhao_xi/support/test_support_1.ply',
                      'zhao_xi/support/test_support_2.ply',
                      'zhao_xi/support/test_support_3.ply',
                      'zhao_xi/support/test_support_4.ply',
                      'zhao_xi/support/test_support_5.ply',
                      'zhao_xi/support/test_support_6.ply',
                      'zhao_xi/support/test_support_7.ply',
                      'zhao_xi/support/test_support_8.ply',
                      'zhao_xi/support/test_support_9.ply',
                      'zhao_xi/support/test_support_10.ply',
                      'zhao_xi/support/test_support_11.ply',
                      'zhao_xi/support/test_support_12.ply',
                      'zhao_xi/support/test_support_13.ply',
                      'zhao_xi/support/test_support_14.ply',
                      'zhao_xi/support/test_support_15.ply',
                      'zhao_xi/support/test_support_16.ply',
                      'zhao_xi/support/test_support_17.ply',
                      'zhao_xi/support/test_support_18.ply',
                      'zhao_xi/support/test_support_19.ply',
                      'zhao_xi/support/test_support_20.ply',
                      'zhao_xi/tunnel/coal_wall/coal_wall.ply',
                      'zhao_xi/tunnel/yunshuxiang/yunshuxiang_vertices.ply',
                      'zhao_xi/tunnel/tongfengxiang/tongfengxiang_vertices.ply']
        for file_name in files_name:
            actor = self.add_actor(self.create_single_actor(file_name))
            # 添加点云对象的可选框
            self.window.add_check_box(file_name, actor, self.point_cloud_actors_checkBoxs)

    def load_label(self):
        # 提示线
        x = 2
        y = 2
        z_1 = -2
        z_2 = 2
        line_source = vtk.vtkLineSource()
        line_source.SetPoint1(x, y, z_1)
        line_source.SetPoint2(x, y, z_2)
        line_mapper = vtk.vtkPolyDataMapper()
        line_mapper.SetInputConnection(line_source.GetOutputPort())
        line_actor = vtk.vtkActor()
        line_actor.SetMapper(line_mapper)
        self.renderer.AddActor(line_actor)
        # 文本
        textActor = vtk.vtkOpenGLBillboardTextActor3D()
        textActor.SetInput("distance : ")
        textActor.GetTextProperty().SetFontSize(24)
        textActor.SetPosition(x, y, (z_1+z_2)/2.0)
        self.renderer.AddActor(textActor)

    def show_point_cloud(self):
        if not self.window.showPointCloud:
            # self.load_dianyun_module()  # 暂时关闭点击时弹窗选文件
            self.Start()
            self.window.viewer_show("PointCloud")
            self.window.showPointCloud = True
            self.window.showVideo = False

    def load_dianyun_module(self):
        files_name = self.get_dianyun_files_path()
        for file_name in files_name:
            actor = self.add_actor(self.create_single_actor(file_name))
            # 添加点云对象的可选框
            self.window.add_check_box(file_name, actor, self.point_cloud_actors_checkBoxs)

    def show_actor(self, actor):  # 目标方法：判断actor是否显示是遍历列表；如果设个标志位数组，性能可以优化。
        if actor in self.renderer.GetActors():
            self.renderer.RemoveActor(actor)
        else:
            self.renderer.AddActor(actor)
        self.renderer.GetRenderWindow().Render()

    def add_actor(self, point_mapper):
        # 创建点云的可视化对象
        point_actor = vtk.vtkActor()
        point_actor.SetMapper(point_mapper)
        point_actor.SetProperty(self.base_property)

        # 存储此点云演员
        self.point_cloud_actors.append(point_actor)

        # 添加点云的演员到渲染器
        self.renderer.AddActor(point_actor)
        return point_actor

    @staticmethod
    def create_single_actor(file_name):
        reader = CustomQVTKRenderWindowInteractor.SUPPORTFILETYPE[file_name.split('.')[-1]]()  # 解析出类的引用
        reader.SetFileName(file_name)

        # 创建点云的可视化对象
        point_mapper = vtk.vtkPolyDataMapper()
        point_mapper.SetInputConnection(reader.GetOutputPort())

        return point_mapper

    def toggled_planeXY(self):
        if not self.show_planeXY:
            # 添加平面 actor 到渲染器
            self.renderer.AddActor(self.plane_actorXY)
            self.show_planeXY = True
        else:
            self.renderer.RemoveActor(self.plane_actorXY)
            self.show_planeXY = False
        self.GetRenderWindow().Render()

    def toggled_planeYZ(self):
        if not self.show_planeYZ:
            # 添加平面 actor 到渲染器
            self.renderer.AddActor(self.plane_actorYZ)
            self.show_planeYZ = True
        else:
            self.renderer.RemoveActor(self.plane_actorYZ)
            self.show_planeYZ = False
        self.GetRenderWindow().Render()

    def toggled_planeXZ(self):
        if not self.show_planeXZ:
            # 添加平面 actor 到渲染器
            self.renderer.AddActor(self.plane_actorXZ)
            self.show_planeXZ = True
        else:
            self.renderer.RemoveActor(self.plane_actorXZ)
            self.show_planeXZ = False
        self.GetRenderWindow().Render()

    def toggled_axes(self):
        if not self.show_axes:
            print("加了坐标轴")
            self.renderer.AddActor(self.cube_axes)  # 这里警告是因为cube_axes不是常规Actor
            self.show_axes = True
        else:
            self.renderer.RemoveActor(self.cube_axes)
            self.show_axes = False
        self.GetRenderWindow().Render()

    def toggled_highlight_point(self):
        if not self.highlight_point:
            self.base_property.SetRepresentationToWireframe()
        else:
            self.base_property.SetRepresentationToSurface()
        for actor in self.point_cloud_actors:
            actor.SetProperty(self.base_property)
        self.renderer.GetRenderWindow().Render()
        self.highlight_point = not self.highlight_point

    def change_property(self):
        self.base_property.SetAmbient(self.window.horizontalSlider_ambient.value() / 100.0)
        self.base_property.SetDiffuse(self.window.horizontalSlider_diffuse.value() / 100.0)
        self.renderer.GetRenderWindow().Render()

    @staticmethod
    def get_dianyun_files_path():
        window = QMainWindow()
        files_path, _ = QFileDialog.getOpenFileNames(window, "选择文件",
                                                     filter=CustomQVTKRenderWindowInteractor.FILEFILETER)
        return files_path

    def keyPressEvent(self, ev):
        self.camera_controller.keypress_processor(ev)
        self.renderer.ResetCameraClippingRange()
        self.renderer.GetRenderWindow().Render()

    def keyReleaseEvent(self, ev):
        self.camera_controller.keyRelease_processor(ev)
        self.renderer.ResetCameraClippingRange()
        self.renderer.GetRenderWindow().Render()

    def wheelEvent(self, ev):
        self.camera_controller.wheelEvent_processor(ev)
        self.renderer.ResetCameraClippingRange()
        self.renderer.GetRenderWindow().Render()

    def mouseMoveEvent(self, ev):
        # ##########标签捕获鼠标移动部分##################################################################
        # 使用Picker获取与鼠标位置相对应的Actor
        # 更新标签位置和文本

        # ##########标签捕获鼠标移动部分##################################################################
        if self.camera_controller.limitedX:
            self.camera_controller.rotate_x(ev)
            self.renderer.ResetCameraClippingRange()
            self.renderer.GetRenderWindow().Render()
        elif self.camera_controller.limitedY:
            self.camera_controller.rotate_y(ev)
            self.renderer.ResetCameraClippingRange()
            self.renderer.GetRenderWindow().Render()
        elif self.camera_controller.limitedRoll:
            self.camera_controller.roll(ev, self.renderer.GetRenderWindow().GetSize()[0] / 2.0,
                                        self.renderer.GetRenderWindow().GetSize()[1] / 2.0)
            self.renderer.ResetCameraClippingRange()
            self.renderer.GetRenderWindow().Render()
        else:
            super().mouseMoveEvent(ev)

    def mousePressEvent(self, ev):
        # ##########################################################
        # 拾取模块
        # self.picker = vtk.vtkPropPicker()
        # self.SetPicker(self.picker)
        # self.picker.Pick(ev.pos().x(), ev.pos().y(), 0, self.renderer)
        # print(self.picker.GetPickPosition())
        # print(self.picker.GetActor())
        # ##########################################################
        if self.camera_controller.unlimited:
            super().mousePressEvent(ev)
        elif ev.button() == Qt.MouseButton.LeftButton:
            self.camera_controller.is_rotating = True
            self.camera_controller.last_x, self.camera_controller.last_y \
                = ev.pos().x(), ev.pos().y()

    def mouseReleaseEvent(self, ev):
        if self.camera_controller.unlimited:
            super().mouseReleaseEvent(ev)
        elif ev.button() == Qt.MouseButton.LeftButton:
            self.camera_controller.is_rotating = False

    def change_viewSpeed_intermediary(self):
        self.camera_controller.change_viewSpeed(self.window.horizontalSlider_viewSpeed.value())

    def change_flySpeed_intermediary(self):
        self.camera_controller.change_flySpeed(self.window.horizontalSlider_flySpeed.value())
