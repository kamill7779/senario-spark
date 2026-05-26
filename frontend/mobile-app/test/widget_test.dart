import 'package:flutter/widgets.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:senario_spark_mobile/app.dart';

void main() {
  testWidgets('starts at login and opens the short-drama shell', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const SenarioSparkApp(enablePlayback: false));

    expect(find.text('SenarioSpark'), findsOneWidget);
    expect(find.text('登录'), findsOneWidget);
    expect(find.text('播放'), findsNothing);

    await tester.tap(find.text('登录'));
    await tester.pumpAndSettle();

    expect(find.text('首页'), findsWidgets);
    expect(find.text('播放'), findsWidgets);
    expect(find.text('我的'), findsWidgets);
  });

  testWidgets('player tab exposes episode playback metadata', (
    WidgetTester tester,
  ) async {
    await tester.pumpWidget(const SenarioSparkApp(enablePlayback: false));
    await tester.tap(find.text('登录'));
    await tester.pumpAndSettle();

    await tester.tap(find.text('播放').last);
    await tester.pumpAndSettle();

    expect(find.text('第3集'), findsOneWidget);
    await tester.drag(find.byType(Scrollable), const Offset(0, -260));
    await tester.pumpAndSettle();

    expect(find.text('上游视频源'), findsOneWidget);
    expect(find.textContaining('http'), findsOneWidget);
  });
}
