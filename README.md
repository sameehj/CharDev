This is a basic char device that was written as a homework assignment during a course of Operating Systems that was held at the Technion Institute Of Technology.

Feel free to use it as you like.

The module functionality is very limited. It supports reading and writing to a buffer with a predefined size (BUFFER_SIZE) , moreover, the module implements two ioctl commands, MY_RESET , MY_RESTART which manipulates the read and write index of the buffer accordingly.
