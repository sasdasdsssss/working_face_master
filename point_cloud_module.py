import time

import vtkmodules.all as vtk
from PySide6.QtWidgets import QMainWindow, QFileDialog, QMessageBox, QCheckBox, QProgressDialog
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
import open3d as o3d
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal, QThread
import math

import Actors
from Actors import *
from camera_controller import CameraController
from readers import *
import scene_initial_info

# 项目模块
from zhao_xi.mine_device import Support
from zhao_xi.tools import *


class WorkerThread(QThread):
    update_progress = Signal(int)

    def __init__(self, parent):
        super().__init__(parent)
        self.interactor = parent

    def run(self):
        for i in range(20):
            support_actor = SupporterActor(scene_initial_info.supporters_filename[i], self.interactor)
            self.interactor.supporter_actors.append(support_actor)
            self.interactor.renderer.AddActor(support_actor)
            progress_value = int((i + 1) * 100 / 20)
            self.update_progress.emit(progress_value)


class CustomQVTKRenderWindowInteractor(QVTKRenderWindowInteractor):
    # 目前支持的文件类型
    SUPPORTFILETYPE = {
        "STL": vtk.vtkSTLReader,  # 存放相应类的引用
        "ply": vtk.vtkPLYReader,
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
        self.renderer.SetBackground(193 / 255, 210 / 255, 240 / 255)
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
        self.cube_axes = vtk.vtkAxesActor()
        # 创建一个坐标轴变换小部件
        axes_transform_widget = vtk.vtkAxesTransformWidget()
        axes_transform_widget.SetInteractor(self)

        # 3.创建背景环境
        self.sphere_actor = SphereActor()
        # self.renderer.AddActor(self.sphere_actor)  # 默认强制有环境图片，暂时不可选
        # --------------------------------------------------------------

        # 存储清空按钮时不会被清除的演员
        self.fixed_actors = [self.plane_actorXY, self.cube_axes]  # 暂时剔除 self.sphere_actor
        # 存储当前加载的点云演员
        self.point_cloud_actors = []
        self.point_cloud_actors_checkBox = []
        self.point_cloud_actors_filename = []
        # 存储当前加载的支撑架演员
        self.supporter_actors = []
        self.scraper_actors = []

        # 正在显示某信息则设置为True,此标志用来帮助释放资源
        self.show_planeXY = False
        self.show_planeYZ = False
        self.show_planeXZ = False
        self.show_axes = False
        self.highlight_point = False  # 是否突出点
        self.supporter_init_flag = False

        # 默认实例化的角色
        self.coal_cutter_actor = CoalCutterActor(scene_initial_info.coal_cutter[0], self)
        self.toggled_planeXY()

    def scraper_init(self):  # 此函数在支撑架初始化中调用
        scraper_actor = ScraperActor('zhao_xi/scraper/FX_1.ply', self)
        self.scraper_actors.append(scraper_actor)
        self.renderer.AddActor(scraper_actor)

    def show_progress_dialog(self):
        progress_dialog = QProgressDialog(self)
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setWindowTitle('加载工作场景...')
        progress_dialog.setLabelText('稍等...')
        progress_dialog.setCancelButton(None)  # 禁用取消按钮
        progress_dialog.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        worker_thread = WorkerThread(self)
        worker_thread.update_progress.connect(progress_dialog.setValue)

        progress_dialog.canceled.connect(worker_thread.terminate)

        worker_thread.start()
        progress_dialog.exec()

    def load_device_and_workplace(self):
        self.add_actor_and_checkbox(scene_initial_info.FX_filename)
        self.add_actor_and_checkbox(scene_initial_info.workplace_filename)

    # def support_init(self):
    #     for i in range(20):
    #         support_actor = SupporterActor(scene_initial_info.supporters_filename[i], self)
    #         self.supporter_actors.append(support_actor)
    #         self.renderer.AddActor(support_actor)

    def support_init(self):
        if not self.supporter_init_flag:
            self.show_progress_dialog()  # 这里面包含了加载
            self.scraper_init()  # 溜子初始化
            self.window.simulate_win_init()  # 这个函数仅是在实例子窗口
            self.supporter_init_flag = True
        else:
            return

    def set_camera_position(self, position):
        self.camera_controller.set_camera_position(position)
        self.renderer.GetRenderWindow().Render()

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
            self.window.add_check_box(file_name, actor, self.point_cloud_actors_checkBox)

    def show_actor(self, actor):  # 目标方法：判断actor是否显示是遍历列表；如果设个标志位数组，性能可以优化。
        if actor in self.renderer.GetActors():
            self.renderer.RemoveActor(actor)
        else:
            self.renderer.AddActor(actor)
        self.renderer.GetRenderWindow().Render()

    def add_actor_and_checkbox(self, files_name):
        for file_name in files_name:
            actor = self.add_actor(self.create_single_actor(file_name))
            # 添加点云对象的可选框
            self.window.add_check_box(file_name, actor, self.point_cloud_actors_checkBox)
            # 记录名称
            self.point_cloud_actors_filename.append(file_name)

    def update_workplace(self):
        for i in range(5):
            self.point_cloud_actors[i].SetMapper(self.create_single_actor(scene_initial_info.workplace_filename[i]))
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

    def move_actor(self, actor: Actors.SupporterActor, dis):
        ticks = 60
        for i in range(ticks):
            actor.move(dis / 60.0)
            self.renderer.GetRenderWindow().Render()
            time.sleep(0.02)

    def show_actors(self, items: list[vtk.vtkActor], flag):
        if not flag:
            for actor in items:
                self.renderer.AddActor(actor)
        else:
            for actor in items:
                self.renderer.RemoveActor(actor)
        self.GetRenderWindow().Render()

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

    def load_camera_info(self, index):
        self.camera_controller.load_camera_info(index)
        self.renderer.GetRenderWindow().Render()
