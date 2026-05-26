import 'package:flutter/material.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(22, 24, 22, 28),
      children: [
        Text(
          '首页',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.w800,
            letterSpacing: 0,
          ),
        ),
        const SizedBox(height: 22),
        const _EpisodeCard(),
      ],
    );
  }
}

class _EpisodeCard extends StatelessWidget {
  const _EpisodeCard();

  @override
  Widget build(BuildContext context) {
    return DecoratedBox(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: const Color(0xFFE8E6E0)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(22),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '今日短剧',
              style: Theme.of(context).textTheme.labelLarge?.copyWith(
                color: const Color(0xFF74746F),
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 10),
            Text(
              '第3集已就绪',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
                letterSpacing: 0,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              '播放页消费上游视频 URL，和生产分发链路保持一致。',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                color: const Color(0xFF5F5F5A),
                height: 1.45,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
