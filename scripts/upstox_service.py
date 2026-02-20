"""
Windows Service for Upstox Token Refresh
This script creates a Windows service that runs the Upstox token refresh scheduler
"""

import os
import sys
import time
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

try:
    import win32serviceutil
    import win32service
    import win32event
    import servicemanager

    WINDOWS_SERVICE_AVAILABLE = True
except ImportError:
    WINDOWS_SERVICE_AVAILABLE = False
    logging.warning(
        "Windows service modules not available. Install pywin32 for Windows service support."
    )


# Configure logging for service
log_dir = project_root / "logs"
if os.getenv('ENVIRONMENT') != 'production':
    log_dir.mkdir(exist_ok=True)

# Using a simpler config here to avoid infinite growth
# Standard RotatingFileHandler should be used if files are needed
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class UpstoxTokenService:
    """Service class that can run as Windows service or standalone"""

    def __init__(self):
        self.scheduler = UpstoxScheduler()
        self.stop_event = None

    def start(self):
        """Start the service"""
        logger.info("Upstox Token Refresh Service starting...")

        try:
            # Start scheduler in background
            import threading

            scheduler_thread = threading.Thread(
                target=self.scheduler.start_scheduler, daemon=True
            )
            scheduler_thread.start()

            logger.info("Upstox Token Refresh Service started successfully")

            # Keep service running
            while True:
                if (
                    WINDOWS_SERVICE_AVAILABLE
                    and self.stop_event
                    and self.stop_event.isSet()
                ):
                    break
                time.sleep(5)

        except Exception as e:
            logger.error(f"Error in service: {e}")
            raise

    def stop(self):
        """Stop the service"""
        logger.info("Upstox Token Refresh Service stopping...")
        self.scheduler.stop_scheduler()
        if self.stop_event:
            self.stop_event.set()
        logger.info("Upstox Token Refresh Service stopped")


if WINDOWS_SERVICE_AVAILABLE:

    class UpstoxWindowsService(win32serviceutil.ServiceFramework):
        """Windows Service wrapper"""

        _svc_name_ = "UpstoxTokenRefreshService"
        _svc_display_name_ = "Upstox Token Refresh Service"
        _svc_description_ = (
            "Automatically refreshes Upstox trading tokens daily at 4 AM"
        )

        def __init__(self, args):
            win32serviceutil.ServiceFramework.__init__(self, args)
            self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
            self.service = UpstoxTokenService()
            self.service.stop_event = self.hWaitStop

        def SvcStop(self):
            """Stop the service"""
            self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
            self.service.stop()
            win32event.SetEvent(self.hWaitStop)

        def SvcDoRun(self):
            """Run the service"""
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, ""),
            )

            try:
                self.service.start()
            except Exception as e:
                logger.error(f"Service error: {e}")
                servicemanager.LogErrorMsg(f"Service error: {e}")


def install_service():
    """Install the Windows service"""
    if not WINDOWS_SERVICE_AVAILABLE:
        print(
            "Windows service modules not available. Install pywin32: pip install pywin32"
        )
        return False

    try:
        win32serviceutil.InstallService(
            UpstoxWindowsService,
            UpstoxWindowsService._svc_name_,
            UpstoxWindowsService._svc_display_name_,
        )
        print(
            f"✅ Service '{UpstoxWindowsService._svc_display_name_}' installed successfully"
        )
        return True
    except Exception as e:
        print(f"❌ Failed to install service: {e}")
        return False


def uninstall_service():
    """Uninstall the Windows service"""
    if not WINDOWS_SERVICE_AVAILABLE:
        print("Windows service modules not available.")
        return False

    try:
        win32serviceutil.RemoveService(UpstoxWindowsService._svc_name_)
        print(
            f"✅ Service '{UpstoxWindowsService._svc_display_name_}' uninstalled successfully"
        )
        return True
    except Exception as e:
        print(f"❌ Failed to uninstall service: {e}")
        return False


def start_service():
    """Start the Windows service"""
    if not WINDOWS_SERVICE_AVAILABLE:
        print("Windows service modules not available.")
        return False

    try:
        win32serviceutil.StartService(UpstoxWindowsService._svc_name_)
        print(
            f"✅ Service '{UpstoxWindowsService._svc_display_name_}' started successfully"
        )
        return True
    except Exception as e:
        print(f"❌ Failed to start service: {e}")
        return False


def stop_service():
    """Stop the Windows service"""
    if not WINDOWS_SERVICE_AVAILABLE:
        print("Windows service modules not available.")
        return False

    try:
        win32serviceutil.StopService(UpstoxWindowsService._svc_name_)
        print(
            f"✅ Service '{UpstoxWindowsService._svc_display_name_}' stopped successfully"
        )
        return True
    except Exception as e:
        print(f"❌ Failed to stop service: {e}")
        return False


def run_standalone():
    """Run as standalone application"""
    print("Running Upstox Token Refresh Service in standalone mode...")
    service = UpstoxTokenService()

    try:
        service.start()
    except KeyboardInterrupt:
        print("\nService interrupted by user")
        service.stop()
    except Exception as e:
        print(f"Service error: {e}")
        service.stop()


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Upstox Token Refresh Service")
    parser.add_argument(
        "--install", action="store_true", help="Install Windows service"
    )
    parser.add_argument(
        "--uninstall", action="store_true", help="Uninstall Windows service"
    )
    parser.add_argument("--start", action="store_true", help="Start Windows service")
    parser.add_argument("--stop", action="store_true", help="Stop Windows service")
    parser.add_argument(
        "--standalone", action="store_true", help="Run in standalone mode"
    )

    args = parser.parse_args()

    if args.install:
        install_service()
    elif args.uninstall:
        uninstall_service()
    elif args.start:
        start_service()
    elif args.stop:
        stop_service()
    elif args.standalone:
        run_standalone()
    else:
        # Default behavior - try to run as Windows service if available
        if WINDOWS_SERVICE_AVAILABLE and len(sys.argv) == 1:
            # Check if we can handle service manager requests
            try:
                win32serviceutil.HandleCommandLine(UpstoxWindowsService)
            except:
                run_standalone()
        else:
            run_standalone()


if __name__ == "__main__":
    main()
