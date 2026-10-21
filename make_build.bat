@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

rem ===== FP 고객관리 구매자 파일 만들기 실행기 =====
rem 사용법 1) 이 파일을 더블클릭 → 이메일·구매번호를 물어보면 입력
rem 사용법 2) make_build.bat --email 구매자@example.com --order 20261016-001   (옵션은 make_build.py와 동일)

if not exist "make_build.py" goto :nofile

rem --- 파이썬 찾기 (py 런처 → python 순서) ---
set "PYCMD="
py -3 --version >nul 2>&1
if not errorlevel 1 set "PYCMD=py -3"
if defined PYCMD goto :found
python --version >nul 2>&1
if not errorlevel 1 set "PYCMD=python"
if defined PYCMD goto :found
goto :nopython

:found
if not "%~1"=="" goto :run_args

echo.
echo [구매자 파일 만들기]
set "EMAIL="
set "ORDER="
set /p EMAIL=구매자 이메일: 
if "%EMAIL%"=="" goto :noemail
set /p ORDER=구매번호 (비워 두면 자동 생성): 
if "%ORDER%"=="" goto :run_noorder
%PYCMD% make_build.py --email "%EMAIL%" --order "%ORDER%"
goto :done

:run_noorder
%PYCMD% make_build.py --email "%EMAIL%"
goto :done

:run_args
%PYCMD% make_build.py %*
goto :done

:noemail
echo 이메일이 입력되지 않아 중단합니다.
goto :done

:nofile
echo.
echo make_build.py 파일을 찾을 수 없습니다.
echo 이 파일(make_build.bat)을 make_build.py와 같은 폴더에 두세요.
goto :done

:nopython
echo.
echo 파이썬(Python)이 설치되어 있지 않습니다. 이 프로그램을 실행하려면 파이썬이 필요합니다.
echo.
choice /c YN /m "지금 설치할까요 (Y=설치, N=취소)"
if errorlevel 2 goto :cancel
where winget >nul 2>&1
if errorlevel 1 goto :manual

echo.
echo 파이썬을 설치합니다. 잠시 기다려 주세요...
winget install -e --id Python.Python.3.12 --accept-package-agreements --accept-source-agreements
if errorlevel 1 goto :manual
echo.
echo 설치가 끝났습니다. 이 창을 닫고 make_build.bat을 다시 실행해 주세요.
goto :done

:manual
echo.
echo 자동 설치를 할 수 없어 파이썬 내려받기 페이지를 엽니다.
echo 설치 첫 화면 아래쪽의 "Add python.exe to PATH"를 꼭 체크한 뒤 설치하세요.
echo 설치가 끝나면 이 창을 닫고 make_build.bat을 다시 실행해 주세요.
start "" "https://www.python.org/downloads/"
goto :done

:cancel
echo 설치를 취소했습니다.

:done
echo.
pause
endlocal
