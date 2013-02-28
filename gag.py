import gui
import random

if __name__ == "__main__":
    test_gui = gui.Gui(virtual_width = 10, virtual_height = 10)
    white = gui.Color()
    gray = gui.Color(0.5, 0.5, 0.5, 0.3)
    blue = gui.Color(0.1, 0.2, 0.7, 0.3)
    red = gui.Color(0.8, 0, 0, 0.3)

    test_gui.fill(white)

    loop_count = 0
    try:
        while True:
            #if not loop_count % 100: test_gui.fill(white)
            time_passed = test_gui.clock.tick(50)
            print "%s fps" % (1000/time_passed)

            test_gui.draw_circle((random.randint(0,640), random.randint(0,480)), 50, fill_color = gray, stroke_color = gray.replace(r=1))
            test_gui.draw_rect(random.randint(0,640), random.randint(0,480), 15, 15, fill_color = blue, stroke_color = blue.replace(a=1))
            test_gui.draw_pixel(random.randint(0,test_gui.virtual_width), random.randint(0,test_gui.virtual_height), red)

            test_gui.update()

            loop_count += 1
    except KeyboardInterrupt:
        test_gui.cairo_surface.write_to_png("example.png")