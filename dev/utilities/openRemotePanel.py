"""
Author: Gaspard BOURGEOIS <gaspard.github.io@free.fr>
Version: 1.0
Date: 22/12/25
"""
import rhinoscriptsyntax as rs
import os

from Rhino.UI import Panels
from System import Guid

def openRemotePanel():
    Panels.OpenPanel(Guid('b45a29b1-4343-4035-989e-044e8580d9cf'))
    #print(Panels.GetOpenPanelIds())
openRemotePanel()
