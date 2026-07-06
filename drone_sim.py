import turtle

screen = turtle.Screen()
screen.title("Space Drone Simulation")
screen.setup(width=800, height=500)
screen.bgcolor("#111116")
screen.tracer(0)

ground = turtle.Turtle()
ground.hideturtle()
ground.penup()
ground.goto(-400, -150)
ground.color("#3a2018")
ground.pendown()
ground.begin_fill()
for _ in range(2):
    ground.forward(800)
    ground.right(90)
    ground.forward(100)
    ground.right(90)
ground.end_fill()

drone = turtle.Turtle()
drone.shape("triangle")
drone.color("white")
drone.shapesize(stretch_wid=1.5, stretch_len=1.5)
drone.penup()
drone.goto(-300, -135)
drone.setheading(90)

screen.update()
turtle.done()
