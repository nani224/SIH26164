#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void run(void) {
  printf("hello, world\n");
  void *buf = malloc(64);
  memcpy(buf, "data", 4);
  free(buf);
}
