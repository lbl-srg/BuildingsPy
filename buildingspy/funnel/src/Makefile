
CC=gcc
CFLAGS=-Wall -Wfloat-equal

SONAME = -soname
UNAME := $(shell uname)
ifeq ($(UNAME),Darwin)
SONAME=-install_name
endif

LIB=libfunnel.so

SRCS=$(foreach fil,*.c, $(fil))
OBJS = algorithmRectangle.o compare.o main.o mkdir_p.o readCSV.o tube.o tubeSize.o


%.o : %.o
	$(CC) -c $(CFLAGS) $< -o $@

test:
	echo $(SRCS)
	echo $(OBJS)

compile:
	$(CC) $(CFLAGS) -fPIC -c $(SRCS)

build: compile
	$(CC) $(CFLAGS) -shared -fPIC -Wl,$(SONAME),$(LIB) -o $(LIB) $(OBJS) -lc
	mkdir -p ../lib64
	mv $(LIB) ../lib64
	$(CC) $(CFLAGS) -o funnel $(OBJS)
	mkdir -p ../bin
	mv funnel ../bin
	rm *.o

clean:
	rm -f *.o ../bin/funnel ../lib64/$(LIB)
