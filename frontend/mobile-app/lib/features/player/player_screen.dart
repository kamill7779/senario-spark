import 'package:flutter/material.dart';

import 'default_episode.dart';
import 'episode_source.dart';
import 'episode_video_player.dart';

class PlayerScreen extends StatelessWidget {
  PlayerScreen({
    super.key,
    this.enablePlayback = true,
    EpisodeSource? source,
  }) : source = source ?? defaultEpisodeSource;

  final bool enablePlayback;
  final EpisodeSource source;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.fromLTRB(22, 24, 22, 28),
      children: [
        Text(
          '播放',
          style: Theme.of(context).textTheme.headlineSmall?.copyWith(
            fontWeight: FontWeight.w800,
            letterSpacing: 0,
          ),
        ),
        const SizedBox(height: 18),
        enablePlayback
            ? EpisodeVideoPlayer(source: source)
            : _PlayerPreviewPlaceholder(source: source),
        const SizedBox(height: 22),
        Text(
          source.title,
          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
            fontWeight: FontWeight.w800,
            letterSpacing: 0,
          ),
        ),
        const SizedBox(height: 8),
        Text(
          source.label,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
            color: const Color(0xFF555550),
            fontWeight: FontWeight.w600,
          ),
        ),
        const SizedBox(height: 14),
        Text(
          source.url.toString(),
          maxLines: 2,
          overflow: TextOverflow.ellipsis,
          style: Theme.of(context).textTheme.bodyMedium?.copyWith(
            color: const Color(0xFF74746F),
            height: 1.45,
          ),
        ),
      ],
    );
  }
}

class _PlayerPreviewPlaceholder extends StatelessWidget {
  const _PlayerPreviewPlaceholder({required this.source});

  final EpisodeSource source;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(22),
      child: AspectRatio(
        aspectRatio: 16 / 9,
        child: ColoredBox(
          color: const Color(0xFF090909),
          child: Center(
            child: Text(
              source.title,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
