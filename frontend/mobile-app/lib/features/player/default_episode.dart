import 'episode_source.dart';

const _configuredEpisodeUrl = String.fromEnvironment(
  'EPISODE_URL',
  defaultValue: 'http://127.0.0.1:8787/%E7%AC%AC3%E9%9B%86.mp4',
);

final defaultEpisodeSource = EpisodeSource.fromUpstreamUrl(
  url: _configuredEpisodeUrl,
);
