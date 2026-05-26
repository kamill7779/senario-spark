import 'package:flutter/material.dart';

class LoginScreen extends StatelessWidget {
  const LoginScreen({super.key, required this.onLogin});

  final VoidCallback onLogin;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(28, 24, 28, 32),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Spacer(),
              Text(
                'SenarioSpark',
                style: Theme.of(context).textTheme.displaySmall?.copyWith(
                  fontWeight: FontWeight.w800,
                  letterSpacing: 0,
                ),
              ),
              const SizedBox(height: 12),
              Text(
                '短剧播放与互动触发',
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                  color: const Color(0xFF5F5F5A),
                  height: 1.4,
                ),
              ),
              const SizedBox(height: 38),
              TextField(
                decoration: _inputDecoration('手机号 / 账号'),
                keyboardType: TextInputType.phone,
              ),
              const SizedBox(height: 14),
              TextField(
                decoration: _inputDecoration('验证码 / 密码'),
                obscureText: true,
              ),
              const SizedBox(height: 22),
              SizedBox(
                width: double.infinity,
                height: 54,
                child: FilledButton(
                  onPressed: onLogin,
                  style: FilledButton.styleFrom(
                    backgroundColor: const Color(0xFF111111),
                    foregroundColor: Colors.white,
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(16),
                    ),
                  ),
                  child: const Text('登录'),
                ),
              ),
              const SizedBox(height: 18),
              Text(
                'MVP 登录入口，后续接入真实账号服务。',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                  color: const Color(0xFF7A7A74),
                ),
              ),
              const Spacer(flex: 2),
            ],
          ),
        ),
      ),
    );
  }

  InputDecoration _inputDecoration(String label) {
    return InputDecoration(
      labelText: label,
      filled: true,
      fillColor: Colors.white,
      contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 18),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: Color(0xFFE7E5DF)),
      ),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(16),
        borderSide: const BorderSide(color: Color(0xFF111111), width: 1.2),
      ),
    );
  }
}
