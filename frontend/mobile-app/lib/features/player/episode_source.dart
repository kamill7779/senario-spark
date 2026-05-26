class EpisodeSource {
  const EpisodeSource._({
    required this.title,
    required this.label,
    required this.url,
  });

  factory EpisodeSource.network({
    required String title,
    required String label,
    required Uri url,
  }) {
    return EpisodeSource._(title: title, label: label, url: url);
  }

  factory EpisodeSource.fromUpstreamUrl({
    required String url,
    String title = '第3集',
    String label = '上游视频源',
  }) {
    return EpisodeSource.network(
      title: title,
      label: label,
      url: Uri.parse(url),
    );
  }

  final String title;
  final String label;
  final Uri url;
}
