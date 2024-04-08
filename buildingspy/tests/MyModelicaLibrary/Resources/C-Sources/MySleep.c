#ifdef _WIN32
#include <Windows.h>
#else
#include <unistd.h>
#endif

int MySleep(int sec)
{
#ifdef _WIN32
  Sleep(sec);
  return 0;
#else
  return sleep(sec);
#endif
}
