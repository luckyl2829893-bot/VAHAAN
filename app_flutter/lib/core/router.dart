import 'package:go_router/go_router.dart';
import '../screens/splash_screen.dart';
import '../screens/login_screen.dart';
import '../screens/home_dashboard.dart';
import '../screens/citizen_portal.dart';
import '../screens/enforcement_hub.dart';
import '../screens/sentinel_mind.dart';
import '../screens/bounty_task_screen.dart';
import '../screens/profile_screen.dart';
import '../screens/wealth_compass_screen.dart';
import '../screens/report_screen.dart';
import '../screens/vault_screen.dart';
import '../screens/dev_portal.dart';

final appRouter = GoRouter(
  initialLocation: '/home',
  routes: [
    GoRoute(
      path: '/',
      builder: (context, state) => const SplashScreen(),
    ),
    GoRoute(
      path: '/login',
      builder: (context, state) => const LoginScreen(),
    ),
    GoRoute(
      path: '/home',
      builder: (context, state) => const HomeDashboard(),
    ),
    GoRoute(
      path: '/citizen',
      builder: (context, state) => const CitizenPortal(),
    ),
    GoRoute(
      path: '/officer',
      builder: (context, state) => const EnforcementHub(),
    ),
    GoRoute(
      path: '/sentinel',
      builder: (context, state) => const SentinelMind(),
    ),
    GoRoute(
      path: '/bounties',
      builder: (context, state) => const BountyTaskScreen(),
    ),
    GoRoute(
      path: '/profile',
      builder: (context, state) => const ProfileScreen(),
    ),
    GoRoute(
      path: '/wealth-compass',
      builder: (context, state) => const WealthCompassScreen(),
    ),
    GoRoute(
      path: '/report',
      builder: (context, state) => const ReportScreen(),
    ),
    GoRoute(
      path: '/vault',
      builder: (context, state) => const VaultScreen(),
    ),
    GoRoute(
      path: '/dev',
      builder: (context, state) => const DevPortal(),
    ),
  ],
);
