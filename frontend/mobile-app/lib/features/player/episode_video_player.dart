import 'package:flutter/material.dart';
import 'package:media_kit/media_kit.dart';
import 'package:media_kit_video/media_kit_video.dart';

import 'episode_source.dart';

class EpisodeVideoPlayer extends StatefulWidget {
  const EpisodeVideoPlayer({super.key, required this.source});

  final EpisodeSource source;

  @override
  State<EpisodeVideoPlayer> createState() => _EpisodeVideoPlayerState();
}

class _EpisodeVideoPlayerState extends State<EpisodeVideoPlayer> {
  late final Player _player;
  late final VideoController _controller;
  Object? _error;
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _player = Player();
    _controller = VideoController(_player);
    _openSource();
  }

  @override
  void didUpdateWidget(EpisodeVideoPlayer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.source.url != widget.source.url) {
      _openSource();
    }
  }

  Future<void> _openSource() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      await _player.open(Media(widget.source.url.toString()), play: false);
      if (mounted) {
        setState(() => _loading = false);
      }
    } catch (error) {
      if (mounted) {
        setState(() {
          _error = error;
          _loading = false;
        });
      }
    }
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(22),
      child: AspectRatio(
        aspectRatio: 16 / 9,
        child: DecoratedBox(
          decoration: const BoxDecoration(color: Color(0xFF090909)),
          child: _buildBody(),
        ),
      ),
    );
  }

  Widget _buildBody() {
    if (_error != null) {
      return _PlayerMessage(
        title: '片源暂时无法打开',
        detail: _error.toString(),
        action: TextButton(onPressed: _openSource, child: const Text('重试')),
      );
    }

    if (_loading) {
      return const _PlayerMessage(title: '正在准备播放', detail: '加载上游片源中');
    }

    return Video(controller: _controller, fit: BoxFit.contain);
  }
}

class _PlayerMessage extends StatelessWidget {
  const _PlayerMessage({required this.title, required this.detail, this.action});

  final String title;
  final String detail;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              title,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w700,
              ),
            ),
            const SizedBox(height: 8),
            Text(
              detail,
              maxLines: 3,
              overflow: TextOverflow.ellipsis,
              textAlign: TextAlign.center,
              style: Theme.of(
                context,
              ).textTheme.bodySmall?.copyWith(color: const Color(0xFFB8B8B8)),
            ),
            if (action != null) ...[const SizedBox(height: 8), action!],
          ],
        ),
      ),
    );
  }
}
