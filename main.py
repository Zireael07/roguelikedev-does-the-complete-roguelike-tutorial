from bearlibterminal import terminal

terminal.open()
terminal.printf(1, 1, 'Hello, world!')
terminal.refresh()

while terminal.read() != terminal.TK_CLOSE:
    pass

terminal.close()