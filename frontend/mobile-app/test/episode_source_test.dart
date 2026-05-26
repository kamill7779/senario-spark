import 'package:flutter_test/flutter_test.dart';
import 'package:senario_spark_mobile/features/player/episode_source.dart';

void main() {
  test('creates a network episode source for upstream delivery', () {
    final source = EpisodeSource.network(
      title: '第3集',
      label: '上游视频源',
      url: Uri.parse('https://cdn.example.com/episodes/3.mp4'),
    );

    expect(source.title, '第3集');
    expect(source.label, '上游视频源');
    expect(source.url.toString(), 'https://cdn.example.com/episodes/3.mp4');
  });

  test('creates default source from configured upstream URL', () {
    final source = EpisodeSource.fromUpstreamUrl(
      url: 'http://127.0.0.1:8787/%E7%AC%AC3%E9%9B%86.mp4',
      title: '第3集',
      label: '上游视频',
    );

    expect(source.title, '第3集');
    expect(source.label, '上游视频');
    expect(source.url.host, '127.0.0.1');
    expect(Uri.decodeComponent(source.url.path), '/第3集.mp4');
  });
}
