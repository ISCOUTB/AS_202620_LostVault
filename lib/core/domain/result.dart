class Result<T> {
  const Result._({this.value, this.error});
  final T? value;
  final String? error;

  bool get isSuccess => error == null;
  bool get isFailure => !isSuccess;

  factory Result.success(T value) => Result._(value: value);
  factory Result.failure(String error) => Result._(error: error);
}
