import 'package:flutter/material.dart';
import '../theme.dart';

class ActionCard extends StatelessWidget {
  const ActionCard({
    super.key,
    required this.image,
    required this.chipIcon,
    required this.chip,
    required this.title,
    required this.subtitle,
    required this.action,
    required this.onTap,
  });

  final String image, chip, title, subtitle, action;
  final IconData chipIcon;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => GestureDetector(
        onTap: onTap,
        child: Container(
          height: 240,
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(
            color: kDark,
            borderRadius: BorderRadius.circular(22),
            image: DecorationImage(
              image: AssetImage(image),
              fit: BoxFit.cover,
              onError: (_, __) {},
              colorFilter: ColorFilter.mode(kDark.withOpacity(.65), BlendMode.srcATop),
            ),
          ),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
              decoration: BoxDecoration(
                  color: Colors.white24, borderRadius: BorderRadius.circular(20)),
              child: Row(mainAxisSize: MainAxisSize.min, children: [
                Icon(chipIcon, color: Colors.white, size: 14),
                const SizedBox(width: 4),
                Flexible(
                  child: Text(chip,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(color: Colors.white, fontSize: 11)),
                ),
              ]),
            ),
            const Spacer(),
            Text(title,
                style: const TextStyle(
                    color: Colors.white, fontSize: 20, fontWeight: FontWeight.bold)),
            const SizedBox(height: 6),
            Text(subtitle, style: const TextStyle(color: Colors.white70, fontSize: 12)),
            const SizedBox(height: 10),
            Row(children: [
              Text(action,
                  style: const TextStyle(
                      color: Colors.white, fontWeight: FontWeight.bold)),
              const SizedBox(width: 4),
              const Icon(Icons.arrow_forward, color: Colors.white, size: 16),
            ]),
          ]),
        ),
      );
}
