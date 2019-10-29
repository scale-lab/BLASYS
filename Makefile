all : _asso.so clean

CC = gcc
CFLAGS = -O2 -fPIC -c
SFLAGS = -shared

ENV=$(shell python3-config --cflags | cut -d " " -f1)
ifeq ($(ENV),)
$(error Cannot find Python environment.,,)
endif

_asso.so: asso/asso_wrap.c asso/driver.c asso/utils.c asso/approx.c
	@$(CC) $(CFLAGS) asso/asso_wrap.c $(ENV)
	@$(CC) $(CFLAGS) asso/driver.c asso/utils.c asso/approx.c
	@$(CC) $(SFLAGS) *.o -o utils/_asso.so

clean:
	@rm -f *.o
