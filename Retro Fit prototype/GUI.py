
from tkinter import *

class GUI(Frame):

    def __init__(self, parent):
        Frame.__init__(self, parent, bg = "white")
        self.setupGUI()

    def setupGUI(self):
        self.display = Label(self, text = "", achor=E,
                             bg = "white", height = 2,
                             )



window = Tk()
window.title("Example")

p = GUI(window)

window.mainloop()