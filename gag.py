import gui

if __name__ == "__main__":
    test_gui = gui.Gui()

    while True:
        time_passed = test_gui.clock.tick(50)
        print "%s fps" % (1000/time_passed)

        test_gui.cairo_drawing_test()
        test_gui.update()