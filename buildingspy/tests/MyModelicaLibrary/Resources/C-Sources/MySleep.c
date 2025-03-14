#ifdef _WIN32
#include <Windows.h>
#else
#include <unistd.h>
#include <time.h>
#endif

int MySleep(int sec)
{
#ifdef _WIN32
  Sleep(sec);
  return 0;
#else
  clock_t start_time = clock();
  while (clock() < start_time + sec*1000);
  return 0;
#endif
}
