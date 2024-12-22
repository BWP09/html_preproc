import typing, os, time

def gen_to_list[**P, T](func: typing.Callable[P, typing.Generator[T, None, None]]) -> typing.Callable[P, list[T]]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> list[T]:
        return list(func(*args, **kwargs))
    
    return wrapper

def mkdir(path: str) -> None:
    os.makedirs(path, exist_ok = True)

def timeit[**P, T](func: typing.Callable[P, T]) -> typing.Callable[P, T]:
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        start = time.time()

        ret = func(*args, **kwargs)
        
        print(f"TIME for {func.__name__!r} -- {(time.time() - start) * 1000 :.5f}ms")

        return ret

    return wrapper