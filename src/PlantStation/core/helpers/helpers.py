def does_throw(func, args):
    try:
        func(*args)
        return True
    except:
        return False
