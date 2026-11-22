import 'dart:io';
import 'package:flutter/material.dart';
import 'package:lostvault/features/objects/public/objects.dart';
import '../theme.dart';

class _Chip extends StatelessWidget {
  const _Chip(this.text);
  final String text;
  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
        decoration: BoxDecoration(
            color: kChip, borderRadius: BorderRadius.circular(10)),
        child: Text(text,
            maxLines: 2,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 11, color: kDark)),
      );
}

class ObjectThumb extends StatelessWidget {
  const ObjectThumb({super.key, required this.path, this.size = 56, this.icon = 28.0});
  final String? path;
  final double size;
  final double icon;

  @override
  Widget build(BuildContext context) {
    final f = path != null ? File(path!) : null;
    final has = f != null && f.existsSync();
    return ClipRRect(
      borderRadius: BorderRadius.circular(8),
      child: SizedBox(
        width: size,
        height: size,
        child: has
            ? Image.file(f, fit: BoxFit.cover)
            : Container(
                color: Colors.grey.shade200,
                child: Icon(Icons.inventory_2_outlined, size: icon)),
      ),
    );
  }
}

class ObjectCard extends StatelessWidget {
  const ObjectCard({super.key, required this.obj, required this.onTap});
  final LostObject obj;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.all(8),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: Colors.grey.shade300),
        ),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            ObjectThumb(path: obj.imagePath),
            const SizedBox(width: 8),
            Expanded(
              child: Text(obj.name,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14)),
            ),
          ]),
          const SizedBox(height: 8),
          _Chip('Ubicación: ${obj.location}'),
          const SizedBox(height: 4),
          _Chip('Hallado: ${obj.foundDate}'),
          const Spacer(),
          Align(
            alignment: Alignment.centerRight,
            child: InkWell(
              onTap: onTap,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                decoration: BoxDecoration(
                    color: kChip, borderRadius: BorderRadius.circular(10)),
                child: const Text('Ver Detalles',
                    style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
              ),
            ),
          ),
        ]),
      );
}
